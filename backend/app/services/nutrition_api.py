"""
Wrapper around USDA FoodData Central and Edamam Food Database APIs.
Strategy: try USDA first, fall back to Edamam if USDA fails, is
unconfigured, or returns no results. Kept separate from router logic
per system_prompt.md ("separate API calling logic from UI/router logic").
"""
import os
from typing import List, Dict

import requests

USDA_API_KEY = os.getenv("USDA_API_KEY")
USDA_BASE = "https://api.nal.usda.gov/fdc/v1"

EDAMAM_FOOD_DB_APP_ID = os.getenv("EDAMAM_FOOD_DB_APP_ID")
EDAMAM_FOOD_DB_APP_KEY = os.getenv("EDAMAM_FOOD_DB_APP_KEY")
EDAMAM_NUTRITION_APP_ID = os.getenv("EDAMAM_NUTRITION_APP_ID")
EDAMAM_NUTRITION_APP_KEY = os.getenv("EDAMAM_NUTRITION_APP_KEY")
EDAMAM_PARSER_URL = "https://api.edamam.com/api/food-database/v2/parser"
EDAMAM_NUTRITION_URL = "https://api.edamam.com/api/nutrition-data"

GRAMS_PER_OZ = 28.3495

# USDA FoodData Central nutrient IDs (fixed by USDA, not configurable)
# USDA reports "calories" under different nutrient IDs depending on data type
# and derivation method. 1008 is standard (SR Legacy), but Foundation Foods
# frequently use Atwater factor IDs instead. Checked in priority order; first
# one present with a nonzero amount wins. 1063 is kilojoules, not kcal.
USDA_ENERGY_KCAL_IDS = [1008, 1062, 2047, 2048]
USDA_ENERGY_KJ_ID = 1063
KCAL_PER_KJ = 1 / 4.184

USDA_NUTRIENT_IDS = {
    "protein_g": 1003,  # Protein
    "carbs_g": 1005,    # Carbohydrate, by difference
    "fat_g": 1004,      # Total lipid (fat)
}

REQUEST_TIMEOUT = 6  # seconds


class NutritionAPIError(Exception):
    """Raised when a provider fails or both providers fail."""


# ---------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------

def _search_usda(query: str, max_results: int, retries: int = 2) -> List[Dict]:
    if not USDA_API_KEY:
        raise NutritionAPIError("USDA_API_KEY not configured")

    params = {
        "query": query,
        "pageSize": max_results,
        "api_key": USDA_API_KEY,
        # Exclude "Branded" by default — that data type has ~48k+ packaged
        # products (candy, drinks, etc.) that drown out plain/generic foods
        # like "egg" or "pineapple, raw" in relevance-ranked results.
        "dataType": "Foundation,SR Legacy,Survey (FNDDS)",
    }

    last_error = None
    for attempt in range(1, retries + 1):
        resp = requests.get(f"{USDA_BASE}/foods/search", params=params, timeout=REQUEST_TIMEOUT)
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            # USDA's gateway occasionally returns a generic nginx 400/5xx for
            # an otherwise-valid request (transient, not query-related) —
            # worth one immediate retry before falling back to Edamam.
            print(
                f"[nutrition_api] USDA search HTTP {resp.status_code} "
                f"(attempt {attempt}/{retries}): {resp.text[:200]}"
            )
            last_error = e
            continue

        foods = resp.json().get("foods", [])
        if not foods:
            raise NutritionAPIError("USDA returned no results")

        return [
            {
                "food_id": f"usda:{f['fdcId']}",
                "name": f.get("description", "Unknown"),
                "source": "usda",
                # USDA search doesn't expose discrete portion units the way
                # Edamam does; nutrients are reported per 100g, so we only
                # offer weight-based units here.
                "units": ["g", "oz"],
            }
            for f in foods
        ]

    raise last_error


def _search_edamam(query: str, max_results: int) -> List[Dict]:
    if not (EDAMAM_FOOD_DB_APP_ID and EDAMAM_FOOD_DB_APP_KEY):
        raise NutritionAPIError("Edamam Food DB credentials not configured")

    resp = requests.get(
        EDAMAM_PARSER_URL,
        params={"app_id": EDAMAM_FOOD_DB_APP_ID, "app_key": EDAMAM_FOOD_DB_APP_KEY, "ingr": query},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    hints = resp.json().get("hints", [])[:max_results]
    if not hints:
        raise NutritionAPIError("Edamam returned no results")

    results = []
    for h in hints:
        food = h.get("food", {})
        measures = h.get("measures", [])
        unit_labels = [m["label"] for m in measures if m.get("label")] or ["Gram"]
        results.append(
            {
                "food_id": f"edamam:{food.get('foodId')}",
                "name": food.get("label", "Unknown"),
                "source": "edamam",
                "units": unit_labels,
            }
        )
    return results


def search_food(query: str, max_results: int = 10) -> List[Dict]:
    try:
        return _search_usda(query, max_results)
    except (NutritionAPIError, requests.RequestException) as e:
        print(f"[nutrition_api] USDA search failed for '{query}': {e}")

    try:
        return _search_edamam(query, max_results)
    except (NutritionAPIError, requests.RequestException) as e:
        raise NutritionAPIError(f"Both USDA and Edamam failed: {e}")


# ---------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------

def _analyze_usda(fdc_id: str, quantity: float, unit: str) -> Dict:
    if not USDA_API_KEY:
        raise NutritionAPIError("USDA_API_KEY not configured")

    resp = requests.get(
        f"{USDA_BASE}/food/{fdc_id}",
        params={"api_key": USDA_API_KEY},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    nutrients_by_id = {}
    for n in data.get("foodNutrients", []):
        nutrient_id = n.get("nutrient", {}).get("id")
        nutrients_by_id[nutrient_id] = n.get("amount", 0)

    unit_norm = unit.strip().lower()
    if unit_norm in ("g", "gram", "grams"):
        grams = quantity
    elif unit_norm in ("oz", "ounce", "ounces"):
        grams = quantity * GRAMS_PER_OZ
    else:
        raise NutritionAPIError(f"USDA analyze only supports g/oz units, got '{unit}'")

    factor = grams / 100.0  # USDA amounts are reported per 100g
    calories = 0
    for nid in USDA_ENERGY_KCAL_IDS:
        if nutrients_by_id.get(nid):
            calories = nutrients_by_id[nid]
            break
    else:
        # No kcal-denominated energy field found — try kJ and convert.
        if nutrients_by_id.get(USDA_ENERGY_KJ_ID):
            calories = nutrients_by_id[USDA_ENERGY_KJ_ID] * KCAL_PER_KJ

    return {
        "calories": round(calories * factor, 2),
        "protein_g": round(nutrients_by_id.get(USDA_NUTRIENT_IDS["protein_g"], 0) * factor, 2),
        "carbs_g": round(nutrients_by_id.get(USDA_NUTRIENT_IDS["carbs_g"], 0) * factor, 2),
        "fat_g": round(nutrients_by_id.get(USDA_NUTRIENT_IDS["fat_g"], 0) * factor, 2),
        "source": "usda",
    }


def _analyze_edamam(food_name: str, quantity: float, unit: str) -> Dict:
    if not (EDAMAM_NUTRITION_APP_ID and EDAMAM_NUTRITION_APP_KEY):
        raise NutritionAPIError("Edamam Nutrition Analysis credentials not configured")

    ingr = f"{quantity} {unit} {food_name}".strip()
    resp = requests.get(
        EDAMAM_NUTRITION_URL,
        params={"app_id": EDAMAM_NUTRITION_APP_ID, "app_key": EDAMAM_NUTRITION_APP_KEY, "ingr": ingr},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    # Classic shape: top-level "totalNutrients" + "calories".
    totals = data.get("totalNutrients")
    if totals:
        return {
            "calories": round(data.get("calories", 0), 2),
            "protein_g": round(totals.get("PROCNT", {}).get("quantity", 0), 2),
            "carbs_g": round(totals.get("CHOCDF", {}).get("quantity", 0), 2),
            "fat_g": round(totals.get("FAT", {}).get("quantity", 0), 2),
            "source": "edamam",
        }

    # Alternate shape some Edamam accounts return: nutrients live nested
    # under ingredients[0].parsed[0].nutrients instead of top-level.
    try:
        nutrients = data["ingredients"][0]["parsed"][0]["nutrients"]
    except (KeyError, IndexError, TypeError):
        raise NutritionAPIError("Edamam could not parse this quantity/unit/food combination")

    return {
        "calories": round(nutrients.get("ENERC_KCAL", {}).get("quantity", 0), 2),
        "protein_g": round(nutrients.get("PROCNT", {}).get("quantity", 0), 2),
        "carbs_g": round(nutrients.get("CHOCDF", {}).get("quantity", 0), 2),
        "fat_g": round(nutrients.get("FAT", {}).get("quantity", 0), 2),
        "source": "edamam",
    }


def analyze_food(food_id: str, food_name: str, quantity: float, unit: str) -> Dict:
    """
    food_id is expected in "usda:<fdcId>" or "edamam:<foodId>" form,
    as returned by search_food(). If the USDA path fails (bad id,
    unsupported unit, API error), we fall back to Edamam's natural-
    language endpoint using food_name instead of the id.
    """
    source, _, raw_id = food_id.partition(":")

    if source == "usda":
        try:
            return _analyze_usda(raw_id, quantity, unit)
        except (NutritionAPIError, requests.RequestException) as e:
            print(f"[nutrition_api] USDA analyze failed for {food_id}: {e}")
            # fall through to Edamam

    try:
        return _analyze_edamam(food_name, quantity, unit)
    except (NutritionAPIError, requests.RequestException) as e:
        raise NutritionAPIError(f"Both USDA and Edamam failed to analyze this food: {e}")
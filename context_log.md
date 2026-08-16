# Nutritional Tracking System - Context Log

*Instructions for the Team: Before starting an AI coding session, provide the AI with the most recent entries from this log. After you finish a feature, add a new entry to the top of this list before opening a Pull Request.*

---

## [2026-07-26] - Initial Setup (Suyash)
- **Action:** Created the GitHub repository, set up branch protection rules (require PRs for `main`).
- **Added:** `system_prompt.md`, `context_log.md`, `.gitignore`, and basic `README.md`.
- **Notes for AI / Team:** The project is initialized but empty. Next steps involve setting up the base FastAPI backend and initializing the React frontend boilerplate.

---
## [2026-07-31] - Phase 2: Auth & Target Generator (Suyash)
- **Added:** app/security.py, app/schemas.py, app/routers/auth.py, app/routers/users.py
- **Changed:** Restructured backend into app/ package (was flat files in backend/ root);
  login now uses OAuth2PasswordRequestForm instead of JSON body so Swagger's Authorize
  button works natively — schemas.UserLogin is now unused as a result; CORS origin set
  to http://localhost:5173 (Vite), not 3000
- **Notes for AI:** Auth uses JWT via python-jose + passlib (bcrypt pinned to 4.0.1 —
  newer bcrypt breaks passlib 1.7.4's version detection). Config values (DB URL, JWT
  secret) read via os.getenv() + python-dotenv, not pydantic-settings, to match existing
  database.py style — no config.py file. GET /users/me/targets computes calorie/macro
  targets via Mifflin-St Jeor + WHO/FAO AMDR midpoints (protein 12%, fat 28%, carbs 60%);
  activity factor is hardcoded to 1.375 (light activity) as a placeholder since users
  table has no activity_level column yet — revisit if per-user accuracy matters later.
  models.py already had DailyLog model + user/logs relationship in place before this
  phase (not new work).

---
## [2026-08-13] - Phase 3: External API Wrappers (Suyash)
- **Added:** app/services/nutrition_api.py, app/routers/food.py; FoodSearchResult,
  FoodAnalyzeRequest, FoodAnalyzeResult schemas in schemas.py
- **Changed:** main.py imports and mounts food.router. /food/search and
  /food/analyze both require auth (Depends(security.get_current_user)), same
  pattern as users.py.
- **Notes for AI:** Strategy is USDA-first, Edamam-fallback. food_id is prefixed
  ("usda:<fdcId>" / "edamam:<foodId>") so /food/analyze knows which provider to
  hit — anything not starting with "usda:" routes straight to Edamam using
  food_name (not strictly validated, but food_id always comes from
  /food/search's own output in practice).

  USDA specifics: search filters dataType to Foundation/SR Legacy/Survey
  (FNDDS), excluding Branded, so results aren't drowned in packaged products.
  A branded-only query correctly returns zero USDA results and falls to
  Edamam. Calorie lookup checks nutrient IDs 1008/1062/2047/2048 in order
  (Foundation Foods often use Atwater-factor IDs instead of the standard
  1008), falling back to ID 1063 (kJ) with unit conversion if none present —
  protein (1003) and fat (1004) IDs are consistent across data types, no
  fallback needed there. USDA analyze only supports g/oz units (nutrients are
  per-100g, no portion-unit conversion built). USDA's gateway occasionally
  returns a transient nginx 400 on an otherwise-valid request — _search_usda()
  retries once before giving up.

  Edamam specifics: Food DB (search/parser) and Nutrition Analysis (analyze)
  are SEPARATE Edamam applications with separate credential pairs, not
  interchangeable. .env has EDAMAM_FOOD_DB_APP_ID/KEY and
  EDAMAM_NUTRITION_APP_ID/KEY (not one shared pair). analyze_food() fallback
  uses food_name + natural-language nutrition-data endpoint, not the Edamam
  foodId directly — that's why FoodAnalyzeRequest requires food_name from the
  frontend. Edamam's nutrition-data response has two possible shapes
  (top-level totalNutrients/calories, or nested under
  ingredients[0].parsed[0].nutrients) — both handled.

  Both search_food() and analyze_food() print the real USDA failure reason
  before falling back to Edamam — check the uvicorn console when debugging
  unexpected fallback behavior.  

---
## [2026-08-15] - Phase 4: Daily Logging & Aggregation (Suyash)
- **Added:** app/routers/logs.py (POST /logs/, DELETE /logs/{log_id}, GET
  /logs/summary?date=YYYY-MM-DD); LogCreate, LogOut, DailySummaryOut,
  MealTypeEnum, ActivityLevelEnum schemas in schemas.py.
- **Changed:** main.py imports and mounts logs.router alongside
  auth/users/food. GET /users/me/targets now takes an optional
  activity_factor query param (ActivityLevelEnum: sedentary 1.2 / light
  1.375 / moderate 1.55 / very_active 1.725 / extra_active 1.9, defaults
  to light/1.375) — previously hardcoded in calculate_targets(). No
  requirements.txt changes — logs.py only needed fastapi/sqlalchemy,
  already present.
- **Notes for AI:** No DB schema/migration needed — daily_logs already had
  meal_type/quantity/unit/date columns from initial setup, and date is a
  Date (not DateTime) column so /logs/summary filters with a direct
  equality match, no truncation logic required. Fixed a stale inline
  comment on DailyLog.meal_type (was "Breakfast, Lunch, Dinner, Snack",
  now "Breakfast, Lunch, Supper, Dinner") to match the actual product
  flow — meal_type itself is an unconstrained String(20) in the DB, but
  LogCreate.meal_type is typed as MealTypeEnum so the API layer only
  accepts those 4 exact values (422 on anything else).

  Design decisions baked into this phase: logging quantity is grams-only
  by design, no per-unit lookup table (e.g. "1 egg", "1 bowl") — frontend
  converts to grams before calling /logs; for Edamam-sourced foods,
  analyze_food() should be called with quantity templated as
  "{quantity}g {food_name}" to keep the same grams-only contract instead
  of relying on Edamam's natural-language quantity parsing. /logs/
  (POST) does NOT call USDA/Edamam itself — it stores whatever
  calories/protein_g/carbs_g/fat_g values it's given, so the intended
  frontend flow is /food/analyze first, then POST those returned values
  to /logs/. activity_factor is per-request only and never persisted
  anywhere (not on the user, not per-log) — a till-date/cumulative
  comparison feature was explicitly deferred in favor of "today only",
  so this lack of persistence isn't a gap yet, but would need revisiting
  if cumulative history is added later. Comparison of consumed-vs-ideal
  is meant to be shown after every single log entry (not gated behind
  logging all 4 meals) by having the frontend call /logs/summary and
  /users/me/targets together after each POST /logs/.

Tested via Swagger UI: register -> login -> targets with varying
  activity_factor (confirmed calorie/macro numbers change) -> food/search
  -> food/analyze -> POST /logs x3 (Lunch, Dinner, and a third entry) ->
  GET /logs/summary (totals matched sum of entries correctly) -> DELETE
  /logs/{id} on one entry -> GET /logs/summary again (deleted entry no
  longer appeared, totals correctly recalculated to reflect only the
  remaining entries). Full CRUD + aggregation loop verified working.
<!-- 
TEMPLATE FOR NEW ENTRIES:
## [YYYY-MM-DD] - Feature Name (Your Name)
- **Added:** [What files/components did you create?]
- **Changed:** [What existing logic did you modify?]
- **Notes for AI:** [What should the next person/AI know? e.g., "Use the new /api/food route for the search bar"]
-->
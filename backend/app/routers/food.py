from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app import models, schemas, security
from app.services.nutrition_api import search_food, analyze_food, NutritionAPIError

router = APIRouter(prefix="/food", tags=["food"])


@router.get("/search", response_model=List[schemas.FoodSearchResult])
def search(
    query: str = Query(..., min_length=1),
    current_user: models.User = Depends(security.get_current_user),
):
    try:
        return search_food(query.strip())
    except NutritionAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/analyze", response_model=schemas.FoodAnalyzeResult)
def analyze(
    payload: schemas.FoodAnalyzeRequest,
    current_user: models.User = Depends(security.get_current_user),
):
    try:
        return analyze_food(
            food_id=payload.food_id,
            food_name=payload.food_name,
            quantity=payload.quantity,
            unit=payload.unit,
        )
    except NutritionAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
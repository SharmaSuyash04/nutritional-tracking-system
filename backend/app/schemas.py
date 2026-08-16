from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional
from datetime import date as date_type

class GenderEnum(str, Enum):
    male = "male"
    female = "female"

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    age: int = Field(..., gt=0, lt=120)
    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    gender: GenderEnum

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    # notice that passowrd not included so that it is not returned in the response
    id: int
    username: str
    age: int
    weight_kg: float
    height_cm: float
    gender: GenderEnum

    class Config:
        from_attributes = True

class TargetsOut(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float

class FoodSearchResult(BaseModel):
    food_id: str        # e.g. "usda:173944" or "edamam:food_abc123"
    name: str
    source: str          # "usda" or "edamam"
    units: List[str]     # e.g. ["g", "oz"] or ["Gram", "Whole", "Large"]

class FoodAnalyzeRequest(BaseModel):
    food_id: str
    food_name: str        # pass through the name from the search result
    quantity: float = Field(..., gt=0)
    unit: str

class FoodAnalyzeResult(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    source: str


class ActivityLevelEnum(float, Enum):
    sedentary = 1.2
    light = 1.375
    moderate = 1.55
    very_active = 1.725
    extra_active = 1.9


# ---- Phase 4: Daily Logging & Aggregation ----

class MealTypeEnum(str, Enum):
    breakfast = "Breakfast"
    lunch = "Lunch"
    supper = "Supper"
    dinner = "Dinner"

class LogCreate(BaseModel):
    date: Optional[date_type] = None  # if omitted, backend defaults to today
    meal_type: MealTypeEnum
    food_name: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)     # always grams
    unit: str = Field(default="g", max_length=50)
    calories: float = Field(..., ge=0)
    protein_g: float = Field(..., ge=0)
    carbs_g: float = Field(..., ge=0)
    fat_g: float = Field(..., ge=0)

class LogOut(BaseModel):
    id: int
    date: date_type
    meal_type: str
    food_name: str
    quantity: float
    unit: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float

    class Config:
        from_attributes = True

class DailySummaryOut(BaseModel):
    date: date_type
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    entries: List[LogOut]
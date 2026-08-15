from pydantic import BaseModel, Field
from enum import Enum
from typing import List

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
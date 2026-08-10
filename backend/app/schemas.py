from pydantic import BaseModel, Field
from enum import Enum

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
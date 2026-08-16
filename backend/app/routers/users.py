from fastapi import APIRouter, Depends

from app import models, schemas, security

router = APIRouter(prefix="/users", tags=["Users"])

def calculate_targets(user: models.User, activity_factor: float) -> schemas.TargetsOut:
    # Mifflin-St Jeor BMR
    if user.gender == "male":
        bmr = 10 * user.weight_kg + 6.25 * user.height_cm - 5 * user.age + 5
    else:
        bmr = 10 * user.weight_kg + 6.25 * user.height_cm - 5 * user.age - 161

    tdee = bmr * activity_factor

    # WHO/FAO acceptable macronutrient distribution ranges (midpoint values)
    protein_pct, fat_pct, carb_pct = 0.12, 0.28, 0.60

    protein_g = (tdee * protein_pct) / 4
    fat_g = (tdee * fat_pct) / 9
    carbs_g = (tdee * carb_pct) / 4

    return schemas.TargetsOut(
        calories=round(tdee, 1),
        protein_g=round(protein_g, 1),
        carbs_g=round(carbs_g, 1),
        fat_g=round(fat_g, 1),
    )

@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(security.get_current_user)):
    return current_user

@router.get("/me/targets", response_model=schemas.TargetsOut)
def get_my_targets(
    activity_factor: schemas.ActivityLevelEnum = schemas.ActivityLevelEnum.light,
    current_user: models.User = Depends(security.get_current_user),
):
    return calculate_targets(current_user, activity_factor.value)
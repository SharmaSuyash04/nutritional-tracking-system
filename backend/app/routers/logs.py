# app/routers/logs.py
from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models, schemas, security
from app.database import get_db

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("/", response_model=schemas.LogOut, status_code=status.HTTP_201_CREATED)
def create_log(
    log_in: schemas.LogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    log_date = log_in.date or date_type.today()

    new_log = models.DailyLog(
        user_id=current_user.id,
        date=log_date,
        meal_type=log_in.meal_type.value,
        food_name=log_in.food_name,
        quantity=log_in.quantity,
        unit=log_in.unit,
        calories=log_in.calories,
        protein_g=log_in.protein_g,
        carbs_g=log_in.carbs_g,
        fat_g=log_in.fat_g,
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    log_entry = (
        db.query(models.DailyLog)
        .filter(
            models.DailyLog.id == log_id,
            models.DailyLog.user_id == current_user.id,
        )
        .first()
    )
    if not log_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Log entry not found"
        )

    db.delete(log_entry)
    db.commit()
    return None


@router.get("/summary", response_model=schemas.DailySummaryOut)
def get_daily_summary(
    date: Optional[date_type] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    target_date = date or date_type.today()

    entries = (
        db.query(models.DailyLog)
        .filter(
            models.DailyLog.user_id == current_user.id,
            models.DailyLog.date == target_date,
        )
        .order_by(models.DailyLog.id)
        .all()
    )

    totals_row = (
        db.query(
            func.coalesce(func.sum(models.DailyLog.calories), 0.0),
            func.coalesce(func.sum(models.DailyLog.protein_g), 0.0),
            func.coalesce(func.sum(models.DailyLog.carbs_g), 0.0),
            func.coalesce(func.sum(models.DailyLog.fat_g), 0.0),
        )
        .filter(
            models.DailyLog.user_id == current_user.id,
            models.DailyLog.date == target_date,
        )
        .first()
    )
    total_calories, total_protein_g, total_carbs_g, total_fat_g = totals_row

    return schemas.DailySummaryOut(
        date=target_date,
        total_calories=total_calories,
        total_protein_g=total_protein_g,
        total_carbs_g=total_carbs_g,
        total_fat_g=total_fat_g,
        entries=entries,
    )
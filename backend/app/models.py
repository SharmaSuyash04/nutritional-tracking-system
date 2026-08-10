# models.py
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    age = Column(Integer, nullable=False)
    weight_kg = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    gender = Column(String(10), nullable=False) # e.g., "male", "female"

    # Establishes a relationship to the DailyLog table
    logs = relationship("DailyLog", back_populates="owner")


class DailyLog(Base):
    __tablename__ = "daily_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    meal_type = Column(String(20), nullable=False) # Breakfast, Lunch, Dinner, Snack
    food_name = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False) # grams, slice, large, etc.
    
    # Nutritional values for this specific portion
    calories = Column(Float, nullable=False)
    protein_g = Column(Float, nullable=False)
    carbs_g = Column(Float, nullable=False)
    fat_g = Column(Float, nullable=False)

    # Links back to the User who created this log
    owner = relationship("User", back_populates="logs")
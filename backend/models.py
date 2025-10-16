from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection URL
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

class Meal(Base):
    """
    Meal model - represents a complete meal with multiple ingredients
    """
    __tablename__ = 'meals'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    servings = Column(Integer, default=1)
    
    # Nutritional totals
    total_protein = Column(Float, default=0)
    total_fat = Column(Float, default=0)
    total_carbs = Column(Float, default=0)
    total_calories = Column(Float, default=0)
    
    # Per serving nutritional values
    protein_per_serving = Column(Float, default=0)
    fat_per_serving = Column(Float, default=0)
    carbs_per_serving = Column(Float, default=0)
    calories_per_serving = Column(Float, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with ingredients
    ingredients = relationship("Ingredient", back_populates="meal", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert meal object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'servings': self.servings,
            'nutritionTotal': {
                'protein': self.total_protein,
                'fat': self.total_fat,
                'carbs': self.total_carbs,
                'calories': self.total_calories
            },
            'nutritionPerServing': {
                'protein': self.protein_per_serving,
                'fat': self.fat_per_serving,
                'carbs': self.carbs_per_serving,
                'calories': self.calories_per_serving
            },
            'ingredients': [ing.to_dict() for ing in self.ingredients],
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }

class Ingredient(Base):
    """
    Ingredient model - represents a single ingredient in a meal
    """
    __tablename__ = 'ingredients'
    
    id = Column(Integer, primary_key=True, index=True)
    meal_id = Column(Integer, ForeignKey('meals.id'), nullable=False)
    
    # USDA FoodData Central ID
    fdc_id = Column(Integer, nullable=False)
    description = Column(String(500), nullable=False)
    brand_name = Column(String(255), default='')
    
    # Amount in grams
    grams = Column(Float, nullable=False)
    
    # Nutritional values (per 100g from USDA)
    protein = Column(Float, default=0)
    fat = Column(Float, default=0)
    carbs = Column(Float, default=0)
    calories = Column(Float, default=0)
    
    # Relationship with meal
    meal = relationship("Meal", back_populates="ingredients")
    
    def to_dict(self):
        """Convert ingredient object to dictionary"""
        return {
            'id': self.id,
            'fdcId': self.fdc_id,
            'description': self.description,
            'brandName': self.brand_name,
            'grams': self.grams,
            'nutrients': {
                'protein': self.protein,
                'fat': self.fat,
                'carbs': self.carbs,
                'calories': self.calories
            }
        }

def init_db():
    """
    Initialize database - create all tables
    """
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

def get_db():
    """
    Get database session
    Use this as a dependency in routes
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    # Run this file directly to create tables
    init_db()

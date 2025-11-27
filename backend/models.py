"""
Database Models for Meal Prep Calculator
=========================================
Defines the database schema using SQLAlchemy ORM (Object-Relational Mapping).

ORM Concept:
    Instead of writing SQL: "CREATE TABLE meals (id INT PRIMARY KEY, ...)"
    We define Python classes, SQLAlchemy generates SQL automatically.
    
Benefits:
    - Write Python instead of SQL
    - Prevents SQL injection
    - Database-agnostic (works with PostgreSQL, MySQL, SQLite)
    - Handles relationships automatically

Tables:
    1. meals - Stores meal plans
    2. ingredients - Stores ingredients (linked to meals via foreign key)
    
Relationship:
    One meal has many ingredients (one-to-many)
    If meal is deleted, ingredients are deleted too (cascade)
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables (.env file)
load_dotenv()

# ============================================================================
# DATABASE CONNECTION
# ============================================================================
# Build connection string from environment variables
# Format: postgresql://username:password@host:port/database_name
# Example: postgresql://postgres:postgres@meal-prep-db:5432/meal_prep_db
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

# Create database engine (connection pool)
# echo=True logs all SQL queries (useful for debugging)
engine = create_engine(DATABASE_URL, echo=True)

# Create session factory (sessions = database connections)
# autocommit=False: We manually control transactions
# autoflush=False: We manually control when changes are written
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
# All our models inherit from this
Base = declarative_base()


# ============================================================================
# MEAL MODEL - Represents a complete meal plan
# ============================================================================
class Meal(Base):
    """
    Meal table - stores saved meal plans.
    
    Columns:
        id: Auto-increment primary key
        name: User-provided meal name
        servings: How many servings this meal makes
        total_*: Total nutrition for entire meal
        *_per_serving: Nutrition divided by servings
        created_at: Timestamp when meal was saved
        updated_at: Timestamp of last modification
        
    Relationships:
        ingredients: List of Ingredient objects (one-to-many)
                    cascade="all, delete-orphan" means:
                    - If meal is deleted, delete its ingredients too
                    - If ingredient is removed from meal.ingredients, delete it
    """
    __tablename__ = 'meals'  # Table name in PostgreSQL
    
    # Primary key (auto-increment)
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic meal information
    name = Column(String(255), nullable=False)  # Max 255 chars, required
    servings = Column(Integer, default=1)       # Default 1 serving
    
    # Total nutritional values (for entire meal)
    total_protein = Column(Float, default=0)
    total_fat = Column(Float, default=0)
    total_carbs = Column(Float, default=0)
    total_calories = Column(Float, default=0)
    
    # Per-serving nutritional values (total / servings)
    protein_per_serving = Column(Float, default=0)
    fat_per_serving = Column(Float, default=0)
    carbs_per_serving = Column(Float, default=0)
    calories_per_serving = Column(Float, default=0)
    
    # Timestamps (automatically managed)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to Ingredient model
    # This creates a "virtual" field meal.ingredients (not a real column)
    # back_populates creates bidirectional relationship
    # cascade controls what happens when meal is deleted
    ingredients = relationship("Ingredient", back_populates="meal", cascade="all, delete-orphan")
    
    def to_dict(self):
        """
        Convert SQLAlchemy model to Python dictionary.
        
        Why:
            jsonify() can't serialize SQLAlchemy objects directly
            Need to convert to dict first
            
        Returns:
            dict: JSON-serializable meal data with nested ingredients
        """
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
            # Convert each ingredient to dict too
            'ingredients': [ing.to_dict() for ing in self.ingredients],
            # Convert datetime to ISO string format
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }


# ============================================================================
# INGREDIENT MODEL - Represents a single ingredient in a meal
# ============================================================================
class Ingredient(Base):
    """
    Ingredient table - stores individual ingredients linked to meals.
    
    Foreign Key Relationship:
        meal_id links to meals.id
        An ingredient MUST belong to a meal (nullable=False)
        If meal is deleted, ingredient is deleted (cascade from Meal model)
        
    Columns:
        id: Primary key (auto-increment)
        meal_id: Foreign key to meals table
        fdc_id: USDA FoodData Central ID (for reference)
        description: Food name (e.g., "Chicken, broilers, breast")
        brand_name: Brand if applicable (e.g., "Tyson")
        grams: Amount in grams
        protein/fat/carbs/calories: Nutritional values (per 100g from USDA)
    """
    __tablename__ = 'ingredients'
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to meals table
    # ForeignKey('meals.id') creates database constraint
    # If you try to insert ingredient with invalid meal_id, database will reject it
    meal_id = Column(Integer, ForeignKey('meals.id'), nullable=False)
    
    # Food identification
    fdc_id = Column(Integer, nullable=False)          # USDA database ID
    description = Column(String(500), nullable=False) # Food name
    brand_name = Column(String(255), default='')      # Optional brand
    
    # Amount
    grams = Column(Float, nullable=False)  # How much of this ingredient
    
    # Nutritional values (per 100g from USDA)
    # These are the "reference values" - not adjusted for grams
    # Actual nutrition = (grams / 100) * these values
    protein = Column(Float, default=0)
    fat = Column(Float, default=0)
    carbs = Column(Float, default=0)
    calories = Column(Float, default=0)
    
    # Relationship back to Meal model
    # ingredient.meal gives you the Meal object this belongs to
    meal = relationship("Meal", back_populates="ingredients")
    
    def to_dict(self):
        """
        Convert ingredient to dictionary.
        
        Returns:
            dict: JSON-serializable ingredient data
        """
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


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def init_db():
    """
    Initialize database - create all tables if they don't exist.
    
    How it works:
        1. Reads all model classes that inherit from Base
        2. Generates CREATE TABLE statements
        3. Executes them in database
        4. If tables already exist, does nothing
        
    Safe to call multiple times (idempotent).
    Called on application startup.
    """
    print("Creating database tables...")
    
    # Create all tables defined in models
    # metadata contains schema information from our models
    # create_all() generates and executes SQL
    Base.metadata.create_all(bind=engine)
    
    print("Database tables created successfully!")


def get_db():
    """
    Get database session (connection).
    
    Generator function (note the yield):
        Used as dependency injection in modern Flask/FastAPI apps
        
    Usage:
        db = SessionLocal()
        try:
            # Use db
        finally:
            db.close()
            
    Or with FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db  # Return session to caller
    finally:
        db.close()  # Always close connection


# ============================================================================
# STANDALONE EXECUTION - Create tables manually
# ============================================================================
if __name__ == "__main__":
    """
    If you run this file directly (python models.py), create tables.
    
    Useful for:
        - Initial database setup
        - Testing database connection
        - Resetting database (drop tables first)
    """
    init_db()
"""
Meal Prep Calculator - Backend API
===================================
This Flask application provides a REST API for:
1. Searching USDA food database
2. Getting nutritional information
3. Saving/retrieving meal plans from PostgreSQL

Architecture:
    Browser → Frontend (Flask) → THIS Backend (Flask) → USDA API
                                      ↓
                                  PostgreSQL
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import sys

# Import our database models (defined in models.py)
from models import Meal, Ingredient, SessionLocal, init_db

# Load environment variables from .env file (API keys, DB credentials, etc.)
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Enable CORS - allows frontend (port 3000) to call backend (port 5000)
# Without this, browser blocks cross-origin requests
CORS(app)

# ============================================================================
# CONFIGURATION - Get settings from environment variables
# ============================================================================
USDA_API_KEY = os.getenv('USDA_API_KEY')  # API key for USDA FoodData Central
USDA_API_URL = os.getenv('USDA_API_URL')  # Base URL: https://api.nal.usda.gov/fdc/v1

# Validate that required configuration exists on startup
# If these are missing, the app cannot function, so exit immediately
if not USDA_API_KEY:
    print("ERROR: USDA_API_KEY not found in environment variables!", file=sys.stderr)
    print("Please check your .env file", file=sys.stderr)
    sys.exit(1)

if not USDA_API_URL:
    print("ERROR: USDA_API_URL not found in environment variables!", file=sys.stderr)
    sys.exit(1)

# Log startup information (helps with debugging)
print(f"Starting Meal Prep Calculator Backend...")
print(f"USDA API URL: {USDA_API_URL}")
print(f"API Key configured: {'Yes' if USDA_API_KEY else 'No'}")

# Initialize database tables if they don't exist
# This runs on every startup but is safe - only creates tables if missing
try:
    init_db()
    print("Database initialized successfully")
except Exception as e:
    print(f"WARNING: Database initialization error: {e}", file=sys.stderr)


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================
@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Kubernetes liveness/readiness probes.
    
    Returns:
        JSON with service status and database connectivity
        
    Example response:
        {
            "status": "healthy",
            "timestamp": "2025-11-26T20:00:00",
            "service": "meal-prep-backend",
            "version": "1.0.0",
            "database": "connected"
        }
    """
    db_status = 'unknown'
    
    # Try to connect to database and execute simple query
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text('SELECT 1'))  # Simple query to test connectivity
        db.close()
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'meal-prep-backend',
        'version': '1.0.0',
        'database': db_status
    }), 200


# ============================================================================
# AUTOCOMPLETE ENDPOINT - Real-time food search suggestions
# ============================================================================
@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    """
    Provides autocomplete suggestions as user types in search box.
    
    Query Parameters:
        q (str): Search query (minimum 2 characters)
        
    Returns:
        JSON array of food suggestions with name and ID
        
    Example:
        GET /autocomplete?q=chicken
        → [
            {"name": "Chicken, broilers, breast", "fdcId": 171477},
            {"name": "Chicken, ground, raw", "fdcId": 171116}
          ]
          
    Flow:
        1. User types "chick" in browser
        2. JavaScript calls /api/autocomplete?q=chick (frontend)
        3. Frontend proxies to this endpoint
        4. We call USDA API
        5. Return simplified list to frontend
        6. Dropdown appears in browser
    """
    # Get query parameter from URL (?q=chicken)
    query = request.args.get('q', '')
    
    # Only search if 2+ characters (reduces unnecessary API calls)
    if len(query) < 2:
        return jsonify([])
    
    try:
        # Call USDA FoodData Central API
        url = f"{USDA_API_URL}/foods/search"
        params = {
            'api_key': USDA_API_KEY,
            'query': query,
            'pageSize': 10,  # Limit to 10 suggestions (performance)
            'dataType': ['Foundation', 'SR Legacy']  # Focus on reliable data
        }
        
        # Make HTTP request with 10 second timeout
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise exception for 4xx/5xx status codes
        data = response.json()
        
        # Extract just what we need: food name and ID
        # Original response has tons of data we don't need for autocomplete
        suggestions = []
        if 'foods' in data:
            for food in data['foods'][:10]:  # Take first 10 results
                suggestions.append({
                    'name': food.get('description', ''),
                    'fdcId': food.get('fdcId', '')
                })
        
        return jsonify(suggestions)
        
    except Exception as e:
        # Log error but return empty array (graceful degradation)
        app.logger.error(f"Autocomplete error: {str(e)}")
        return jsonify([])


# ============================================================================
# SEARCH ENDPOINT - Full food search with nutritional data
# ============================================================================
@app.route('/api/search', methods=['GET'])
def search_food():
    """
    Search for food items with complete nutritional information.
    
    Query Parameters:
        query (str): Search term (e.g., "chicken breast")
        
    Returns:
        JSON with search results including full nutrition data
        
    Example:
        GET /api/search?query=chicken
        → {
            "totalResults": 1523,
            "currentResults": 10,
            "foods": [
                {
                    "fdcId": 171477,
                    "description": "Chicken, broilers, breast",
                    "nutrients": {
                        "protein": 31.02,
                        "fat": 3.57,
                        "carbs": 0,
                        "calories": 165
                    }
                }
            ]
          }
    """
    # Get search query from URL parameters
    query = request.args.get('query', '')
    
    if not query:
        return jsonify({'error': 'Missing query parameter'}), 400
    
    try:
        # Call USDA API
        url = f"{USDA_API_URL}/foods/search"
        params = {
            'api_key': USDA_API_KEY,
            'query': query,
            'pageSize': 10,
            'dataType': ['Foundation', 'SR Legacy']
        }
        
        print(f"Searching USDA API for: {query}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Process results - extract nutrition from complex USDA format
        foods = []
        for food in data.get('foods', []):
            foods.append({
                'fdcId': food.get('fdcId'),
                'description': food.get('description'),
                'brandName': food.get('brandName', ''),
                'dataType': food.get('dataType', ''),
                # extract_nutrients() converts USDA format to our simple format
                'nutrients': extract_nutrients(food.get('foodNutrients', []))
            })
        
        print(f"Found {len(foods)} results")
        
        return jsonify({
            'totalResults': data.get('totalHits', 0),
            'currentResults': len(foods),
            'foods': foods
        }), 200
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'USDA API request timed out'}), 504
    except requests.exceptions.RequestException as e:
        print(f"Error calling USDA API: {str(e)}", file=sys.stderr)
        return jsonify({'error': f'Error calling USDA API: {str(e)}'}), 500


# ============================================================================
# FOOD DETAILS ENDPOINT - Get detailed info for specific food
# ============================================================================
@app.route('/api/food/<int:fdc_id>', methods=['GET'])
def get_food_details(fdc_id):
    """
    Get detailed nutritional information for a specific food item.
    
    Path Parameters:
        fdc_id (int): FoodData Central ID (unique identifier)
        
    Returns:
        JSON with complete food details
        
    Example:
        GET /api/food/171477
        → Full nutritional profile for that food
    """
    try:
        url = f"{USDA_API_URL}/food/{fdc_id}"
        params = {'api_key': USDA_API_KEY}
        
        print(f"Fetching details for FDC ID: {fdc_id}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        return jsonify({
            'fdcId': data.get('fdcId'),
            'description': data.get('description'),
            'brandName': data.get('brandName', ''),
            'dataType': data.get('dataType', ''),
            'nutrients': extract_nutrients(data.get('foodNutrients', []))
        }), 200
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching food details: {str(e)}", file=sys.stderr)
        return jsonify({'error': f'Error fetching food details: {str(e)}'}), 500


# ============================================================================
# CALCULATE ENDPOINT - Calculate meal nutrition
# ============================================================================
@app.route('/api/calculate', methods=['POST'])
def calculate_meal():
    """
    Calculate total and per-serving nutrition for a meal.
    
    Request Body:
        {
            "ingredients": [
                {"fdcId": 123, "description": "Chicken", "grams": 200, "nutrients": {...}},
                {"fdcId": 456, "description": "Rice", "grams": 150, "nutrients": {...}}
            ],
            "servings": 4
        }
        
    Returns:
        JSON with total and per-serving nutritional values
        
    Logic:
        1. USDA values are "per 100g"
        2. Calculate actual amount: (grams / 100) * nutrient_value
        3. Sum all ingredients
        4. Divide by servings for per-serving values
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    ingredients = data.get('ingredients', [])
    servings = data.get('servings', 1)
    
    if not ingredients or servings <= 0:
        return jsonify({'error': 'Invalid data: ingredients required and servings must be > 0'}), 400
    
    # Calculate totals for all ingredients
    totals = {
        'protein': 0,
        'fat': 0,
        'carbs': 0,
        'calories': 0
    }
    
    for ingredient in ingredients:
        grams = ingredient.get('grams', 0)
        nutrients = ingredient.get('nutrients', {})
        
        # USDA values are per 100g, so calculate actual amount
        # Example: 200g chicken with 31g protein per 100g
        #          = (200/100) * 31 = 62g protein
        factor = grams / 100
        
        totals['protein'] += nutrients.get('protein', 0) * factor
        totals['fat'] += nutrients.get('fat', 0) * factor
        totals['carbs'] += nutrients.get('carbs', 0) * factor
        totals['calories'] += nutrients.get('calories', 0) * factor
    
    # Calculate per serving by dividing totals
    per_serving = {
        'protein': round(totals['protein'] / servings, 2),
        'fat': round(totals['fat'] / servings, 2),
        'carbs': round(totals['carbs'] / servings, 2),
        'calories': round(totals['calories'] / servings, 2)
    }
    
    result = {
        'total': {
            'protein': round(totals['protein'], 2),
            'fat': round(totals['fat'], 2),
            'carbs': round(totals['carbs'], 2),
            'calories': round(totals['calories'], 2)
        },
        'perServing': per_serving,
        'servings': servings
    }
    
    print(f"Calculated meal: {result}")
    
    return jsonify(result), 200


# ============================================================================
# SAVE MEAL ENDPOINT - Persist meal to database
# ============================================================================
@app.route('/api/meals', methods=['POST'])
def save_meal():
    """
    Save a meal plan to PostgreSQL database.
    
    Request Body:
        {
            "name": "My Healthy Meal",
            "servings": 4,
            "ingredients": [...],
            "nutritionTotal": {...},
            "nutritionPerServing": {...}
        }
        
    Returns:
        JSON with saved meal including generated database ID
        
    Database Transaction:
        1. Create Meal record (gets auto-increment ID)
        2. Create Ingredient records linked to Meal (foreign key)
        3. Commit transaction (all or nothing)
        4. Return saved meal with ID
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    # Get database session (connection)
    db = SessionLocal()
    
    try:
        # Create Meal object (SQLAlchemy ORM)
        meal = Meal(
            name=data.get('name', 'Unnamed Meal'),
            servings=data.get('servings', 1),
            total_protein=data.get('nutritionTotal', {}).get('protein', 0),
            total_fat=data.get('nutritionTotal', {}).get('fat', 0),
            total_carbs=data.get('nutritionTotal', {}).get('carbs', 0),
            total_calories=data.get('nutritionTotal', {}).get('calories', 0),
            protein_per_serving=data.get('nutritionPerServing', {}).get('protein', 0),
            fat_per_serving=data.get('nutritionPerServing', {}).get('fat', 0),
            carbs_per_serving=data.get('nutritionPerServing', {}).get('carbs', 0),
            calories_per_serving=data.get('nutritionPerServing', {}).get('calories', 0)
        )
        
        # Add meal to database (not committed yet)
        db.add(meal)
        db.flush()  # Get the auto-generated ID without committing
        
        # Create Ingredient records linked to this meal
        for ing_data in data.get('ingredients', []):
            ingredient = Ingredient(
                meal_id=meal.id,  # Foreign key to meal
                fdc_id=ing_data.get('fdcId'),
                description=ing_data.get('description', ''),
                brand_name=ing_data.get('brandName', ''),
                grams=ing_data.get('grams', 0),
                protein=ing_data.get('nutrients', {}).get('protein', 0),
                fat=ing_data.get('nutrients', {}).get('fat', 0),
                carbs=ing_data.get('nutrients', {}).get('carbs', 0),
                calories=ing_data.get('nutrients', {}).get('calories', 0)
            )
            db.add(ingredient)
        
        # Commit transaction - saves everything to database
        db.commit()
        db.refresh(meal)  # Reload from DB to get relationships
        
        print(f"Saved meal to database: {meal.name} (ID: {meal.id})")
        
        return jsonify(meal.to_dict()), 201
        
    except Exception as e:
        # If anything fails, rollback entire transaction
        db.rollback()
        print(f"Error saving meal: {str(e)}", file=sys.stderr)
        return jsonify({'error': f'Error saving meal: {str(e)}'}), 500
    finally:
        # Always close database connection
        db.close()


# ============================================================================
# GET MEALS ENDPOINT - Retrieve meal history
# ============================================================================
@app.route('/api/meals', methods=['GET'])
def get_meals():
    """
    Get all saved meals from database, ordered by most recent first.
    
    Returns:
        JSON array of all meals with ingredients
        
    Example:
        GET /api/meals
        → {
            "total": 5,
            "meals": [...]
          }
    """
    db = SessionLocal()
    
    try:
        # Query all meals, newest first
        # SQLAlchemy automatically loads ingredients (relationship)
        meals = db.query(Meal).order_by(Meal.created_at.desc()).all()
        
        return jsonify({
            'total': len(meals),
            'meals': [meal.to_dict() for meal in meals]
        }), 200
        
    except Exception as e:
        print(f"Error fetching meals: {str(e)}", file=sys.stderr)
        return jsonify({'error': f'Error fetching meals: {str(e)}'}), 500
    finally:
        db.close()


# ============================================================================
# GET SINGLE MEAL ENDPOINT - Retrieve specific meal
# ============================================================================
@app.route('/api/meals/<int:meal_id>', methods=['GET'])
def get_meal(meal_id):
    """
    Get a specific meal by database ID.
    
    Path Parameters:
        meal_id (int): Database ID of the meal
        
    Returns:
        JSON with meal details including all ingredients
    """
    db = SessionLocal()
    
    try:
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        
        if not meal:
            return jsonify({'error': 'Meal not found'}), 404
        
        return jsonify(meal.to_dict()), 200
        
    except Exception as e:
        print(f"Error fetching meal: {str(e)}", file=sys.stderr)
        return jsonify({'error': f'Error fetching meal: {str(e)}'}), 500
    finally:
        db.close()


# ============================================================================
# DELETE MEAL ENDPOINT - Remove meal from database
# ============================================================================
@app.route('/api/meals/<int:meal_id>', methods=['DELETE'])
def delete_meal(meal_id):
    """
    Delete a meal and all its ingredients from database.
    
    Path Parameters:
        meal_id (int): Database ID of meal to delete
        
    Returns:
        JSON success message
        
    Note:
        Ingredients are automatically deleted due to cascade="all, delete-orphan"
        in the Meal model relationship definition.
    """
    db = SessionLocal()
    
    try:
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        
        if not meal:
            return jsonify({'error': 'Meal not found'}), 404
        
        # Delete meal (ingredients deleted automatically via cascade)
        db.delete(meal)
        db.commit()
        
        print(f"Deleted meal from database: ID {meal_id}")
        
        return jsonify({'message': 'Meal deleted successfully'}), 200
        
    except Exception as e:
        db.rollback()
        print(f"Error deleting meal: {str(e)}", file=sys.stderr)
        return jsonify({'error': f'Error deleting meal: {str(e)}'}), 500
    finally:
        db.close()


# ============================================================================
# HELPER FUNCTION - Extract nutrients from USDA response
# ============================================================================
def extract_nutrients(food_nutrients):
    """
    Convert USDA's complex nutrient format to our simple format.
    
    USDA Format:
        [
            {"nutrientName": "Protein", "value": 31.02, "unitName": "G"},
            {"nutrientName": "Total lipid (fat)", "value": 3.57, "unitName": "G"},
            ...hundreds more nutrients...
        ]
        
    Our Format:
        {
            "protein": 31.02,
            "fat": 3.57,
            "carbs": 0,
            "calories": 165
        }
        
    Args:
        food_nutrients (list): Array of nutrient objects from USDA
        
    Returns:
        dict: Simplified nutrient values (protein, fat, carbs, calories)
    """
    nutrients = {
        'protein': 0,
        'fat': 0,
        'carbs': 0,
        'calories': 0
    }
    
    # Map USDA nutrient names to our simplified names
    nutrient_mapping = {
        'Protein': 'protein',
        'Total lipid (fat)': 'fat',
        'Carbohydrate, by difference': 'carbs',
        'Energy': 'calories'
    }
    
    # Loop through all nutrients USDA returns (100+)
    # We only care about the 4 we mapped above
    for nutrient in food_nutrients:
        nutrient_name = nutrient.get('nutrientName', '')
        
        # Check if this nutrient is one we care about
        for usda_name, our_name in nutrient_mapping.items():
            if usda_name in nutrient_name:
                nutrients[our_name] = nutrient.get('value', 0)
                break  # Found it, stop looking
    
    return nutrients


# ============================================================================
# APPLICATION STARTUP
# ============================================================================
if __name__ == '__main__':
    # Get port from environment variable (default 5000)
    port = int(os.getenv('PORT', 5000))
    
    # Debug mode: auto-reload on code changes, detailed error pages
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    print(f"\n{'='*50}")
    print(f"Starting Flask Server on port {port}")
    print(f"Debug mode: {debug}")
    print(f"{'='*50}\n")
    
    # Start Flask development server
    # host='0.0.0.0' allows external connections (required for Docker)
    app.run(host='0.0.0.0', port=port, debug=debug)
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import sys

# Import database models
from models import Meal, Ingredient, SessionLocal, init_db

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configuration from environment variables
USDA_API_KEY = os.getenv('USDA_API_KEY')
USDA_API_URL = os.getenv('USDA_API_URL')

# Validate configuration on startup
if not USDA_API_KEY:
    print("ERROR: USDA_API_KEY not found in environment variables!", file=sys.stderr)
    print("Please check your .env file", file=sys.stderr)
    sys.exit(1)

if not USDA_API_URL:
    print("ERROR: USDA_API_URL not found in environment variables!", file=sys.stderr)
    sys.exit(1)

print(f"Starting Meal Prep Calculator Backend...")
print(f"USDA API URL: {USDA_API_URL}")
print(f"API Key configured: {'Yes' if USDA_API_KEY else 'No'}")

# Initialize database tables if they don't exist
try:
    init_db()
    print("Database initialized successfully")
except Exception as e:
    print(f"WARNING: Database initialization error: {e}", file=sys.stderr)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify service is running"""
    db_status = 'unknown'
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text('SELECT 1'))
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

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    """
    Autocomplete endpoint for food search
    Returns list of food suggestions as user types
    """
    query = request.args.get('q', '')
    
    if len(query) < 2:  # Only search if 2+ characters
        return jsonify([])
    
    try:
        # USDA API search endpoint
        url = f"{USDA_API_URL}/foods/search"
        params = {
            'api_key': USDA_API_KEY,
            'query': query,
            'pageSize': 10,  # Limit to 10 suggestions
            'dataType': ['Foundation', 'SR Legacy']
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract just food names for autocomplete
        suggestions = []
        if 'foods' in data:
            for food in data['foods'][:10]:
                suggestions.append({
                    'name': food.get('description', ''),
                    'fdcId': food.get('fdcId', '')
                })
        
        return jsonify(suggestions)
        
    except Exception as e:
        app.logger.error(f"Autocomplete error: {str(e)}")
        return jsonify([])


@app.route('/api/search', methods=['GET'])
def search_food():
    """
    Search for food items using USDA FoodData Central API
    Query parameter: query (string) - search term
    Returns: List of food items with basic nutritional info
    """
    query = request.args.get('query', '')
    
    if not query:
        return jsonify({'error': 'Missing query parameter'}), 400
    
    try:
        # Call USDA API
        url = f"{USDA_API_URL}/foods/search"
        params = {
            'api_key': USDA_API_KEY,
            'query': query,
            'pageSize': 10,  # Limit to 10 results
            'dataType': ['Foundation', 'SR Legacy']  # Focus on reliable data sources
        }
        
        print(f"Searching USDA API for: {query}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Process results into simplified format
        foods = []
        for food in data.get('foods', []):
            foods.append({
                'fdcId': food.get('fdcId'),
                'description': food.get('description'),
                'brandName': food.get('brandName', ''),
                'dataType': food.get('dataType', ''),
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

@app.route('/api/food/<int:fdc_id>', methods=['GET'])
def get_food_details(fdc_id):
    """
    Get detailed information for a specific food item
    Path parameter: fdc_id (integer) - FoodData Central ID
    Returns: Detailed food information with full nutritional data
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

@app.route('/api/calculate', methods=['POST'])
def calculate_meal():
    """
    Calculate nutritional values for a meal
    Request body: {
        ingredients: [{fdcId, description, grams, nutrients}],
        servings: integer
    }
    Returns: Total nutritional values and per-serving breakdown
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    ingredients = data.get('ingredients', [])
    servings = data.get('servings', 1)
    
    if not ingredients or servings <= 0:
        return jsonify({'error': 'Invalid data: ingredients required and servings must be > 0'}), 400
    
    # Calculate totals
    totals = {
        'protein': 0,
        'fat': 0,
        'carbs': 0,
        'calories': 0
    }
    
    for ingredient in ingredients:
        grams = ingredient.get('grams', 0)
        nutrients = ingredient.get('nutrients', {})
        
        # Calculate based on weight (USDA values are per 100g)
        factor = grams / 100
        
        totals['protein'] += nutrients.get('protein', 0) * factor
        totals['fat'] += nutrients.get('fat', 0) * factor
        totals['carbs'] += nutrients.get('carbs', 0) * factor
        totals['calories'] += nutrients.get('calories', 0) * factor
    
    # Calculate per serving
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

@app.route('/api/meals', methods=['POST'])
def save_meal():
    """
    Save a meal to database
    Request body: {
        name: string,
        ingredients: array,
        nutritionTotal: object,
        nutritionPerServing: object,
        servings: integer
    }
    Returns: Saved meal with generated ID
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    db = SessionLocal()
    
    try:
        # Create meal object
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
        
        # Add meal to database
        db.add(meal)
        db.flush()  # Get the meal ID
        
        # Add ingredients
        for ing_data in data.get('ingredients', []):
            ingredient = Ingredient(
                meal_id=meal.id,
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
        
        db.commit()
        db.refresh(meal)
        
        print(f"Saved meal to database: {meal.name} (ID: {meal.id})")
        
        return jsonify(meal.to_dict()), 201
        
    except Exception as e:
        db.rollback()
        print(f"Error saving meal: {str(e)}", file=sys.stderr)
        return jsonify({'error': f'Error saving meal: {str(e)}'}), 500
    finally:
        db.close()

@app.route('/api/meals', methods=['GET'])
def get_meals():
    """
    Retrieve meal history from database
    Returns: Array of all saved meals
    """
    db = SessionLocal()
    
    try:
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

@app.route('/api/meals/<int:meal_id>', methods=['GET'])
def get_meal(meal_id):
    """
    Get a specific meal by ID
    Path parameter: meal_id (integer)
    Returns: Meal details with ingredients
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

@app.route('/api/meals/<int:meal_id>', methods=['DELETE'])
def delete_meal(meal_id):
    """
    Delete a meal from database
    Path parameter: meal_id (integer)
    Returns: Success message
    """
    db = SessionLocal()
    
    try:
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        
        if not meal:
            return jsonify({'error': 'Meal not found'}), 404
        
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

def extract_nutrients(food_nutrients):
    """
    Extract key nutritional values from USDA food nutrient data
    Args: food_nutrients (list) - Array of nutrient objects from USDA API
    Returns: Dictionary with protein, fat, carbs, and calories
    """
    nutrients = {
        'protein': 0,
        'fat': 0,
        'carbs': 0,
        'calories': 0
    }
    
    # Mapping of USDA nutrient names to our simplified names
    nutrient_mapping = {
        'Protein': 'protein',
        'Total lipid (fat)': 'fat',
        'Carbohydrate, by difference': 'carbs',
        'Energy': 'calories'
    }
    
    for nutrient in food_nutrients:
        nutrient_name = nutrient.get('nutrientName', '')
        
        for usda_name, our_name in nutrient_mapping.items():
            if usda_name in nutrient_name:
                nutrients[our_name] = nutrient.get('value', 0)
                break
    
    return nutrients

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    print(f"\n{'='*50}")
    print(f"Starting Flask Server on port {port}")
    print(f"Debug mode: {debug}")
    print(f"{'='*50}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
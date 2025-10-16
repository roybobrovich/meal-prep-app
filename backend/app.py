from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import sys

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configuration from environment variables
USDA_API_KEY = os.getenv('USDA_API_KEY')
USDA_API_URL = os.getenv('USDA_API_URL')

# In-memory storage for meals (temporary - will be replaced with database)
meals_history = []

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

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify service is running"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'meal-prep-backend',
        'version': '1.0.0'
    }), 200

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
    Save a meal to history (temporary in-memory storage)
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
    
    meal = {
        'id': len(meals_history) + 1,
        'name': data.get('name', 'Unnamed Meal'),
        'ingredients': data.get('ingredients', []),
        'nutritionTotal': data.get('nutritionTotal', {}),
        'nutritionPerServing': data.get('nutritionPerServing', {}),
        'servings': data.get('servings', 1),
        'createdAt': datetime.now().isoformat()
    }
    
    meals_history.append(meal)
    
    print(f"Saved meal: {meal['name']} (ID: {meal['id']})")
    
    return jsonify(meal), 201

@app.route('/api/meals', methods=['GET'])
def get_meals():
    """
    Retrieve meal history
    Returns: Array of all saved meals
    """
    return jsonify({
        'total': len(meals_history),
        'meals': meals_history
    }), 200

@app.route('/api/meals/<int:meal_id>', methods=['DELETE'])
def delete_meal(meal_id):
    """
    Delete a meal from history
    Path parameter: meal_id (integer)
    Returns: Success message
    """
    global meals_history
    
    meal = next((m for m in meals_history if m['id'] == meal_id), None)
    
    if not meal:
        return jsonify({'error': 'Meal not found'}), 404
    
    meals_history = [m for m in meals_history if m['id'] != meal_id]
    
    print(f"Deleted meal ID: {meal_id}")
    
    return jsonify({'message': 'Meal deleted successfully'}), 200

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
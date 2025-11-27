"""
Meal Prep Calculator - Frontend Web Application
===============================================
This Flask application serves the user interface (HTML templates).

Architecture:
    Browser ↔ THIS Frontend (Flask on port 3000) ↔ Backend API (Flask on port 5000)
    
Key Responsibilities:
    1. Serve HTML pages to browser
    2. Handle form submissions
    3. Proxy API calls to backend
    4. Manage user sessions (meal-building state)
    
Why Separate Frontend/Backend?
    - Microservices architecture (separation of concerns)
    - Frontend handles presentation, Backend handles data/logic
    - Can scale independently
    - Backend API can serve mobile apps, other frontends
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests
import os

# Initialize Flask application
app = Flask(__name__)

# Secret key for session encryption (stores user data in browser cookie)
# In production, this should be a random string from environment variable
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Backend API URL - where our REST API lives
# In Kubernetes: http://meal-prep-backend:5000 (service discovery)
# Locally: http://localhost:5000
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')


# ============================================================================
# AUTOCOMPLETE PROXY - Forwards autocomplete requests to backend
# ============================================================================
@app.route('/api/autocomplete', methods=['GET'])
def autocomplete_proxy():
    """
    Proxy autocomplete requests from browser to backend API.
    
    Why Proxy?
        Browser makes AJAX call to /api/autocomplete (same origin as HTML page)
        We forward to backend on different port/host
        Backend does the actual USDA API call
        We return results to browser
        
    Flow:
        Browser JS → /api/autocomplete → Backend /autocomplete → USDA API
        
    Query Parameters:
        q (str): Search query from user input
        
    Returns:
        JSON array of food suggestions
    """
    query = request.args.get('q', '')
    
    try:
        # Forward request to backend
        # f-string creates: http://meal-prep-backend:5000/autocomplete?q=chicken
        response = requests.get(f'{BACKEND_URL}/autocomplete', params={'q': query})
        
        # Return backend's response to browser
        return jsonify(response.json())
        
    except Exception as e:
        # Log error but don't crash - return empty array for graceful degradation
        app.logger.error(f"Autocomplete proxy error: {str(e)}")
        return jsonify([])


# ============================================================================
# HOME PAGE
# ============================================================================
@app.route('/')
def index():
    """
    Main landing page - shows menu of options.
    
    Renders: templates/index.html
    """
    return render_template('index.html')


# ============================================================================
# SEARCH PAGE
# ============================================================================
@app.route('/search', methods=['GET', 'POST'])
def search():
    """
    Search for food in USDA database.
    
    GET:  Show search form (templates/search.html with autocomplete)
    POST: Submit search to backend, show results
    
    Form Flow:
        1. User types in search box (autocomplete helps)
        2. User clicks "Search" button (form submits)
        3. POST request here with form data
        4. We call backend API
        5. Render results page
    """
    if request.method == 'POST':
        # Get search query from form submission
        # request.form is a dictionary of form field names/values
        query = request.form.get('query', '')
        
        try:
            # Call backend API search endpoint
            response = requests.get(f'{BACKEND_URL}/api/search', params={'query': query})
            results = response.json()
            
            # Render results template with data
            return render_template('search_results.html', 
                                 foods=results.get('foods', []), 
                                 query=query)
        except Exception as e:
            # Show error page if backend call fails
            return render_template('error.html', error=str(e))
    
    # GET request - just show the search form
    return render_template('search.html')


# ============================================================================
# CREATE MEAL PAGE - Build a meal by adding ingredients
# ============================================================================
@app.route('/create-meal', methods=['GET'])
def create_meal_page():
    """
    Show the meal builder interface.
    
    Session State:
        We store the current meal being built in Flask session (browser cookie)
        This persists across page refreshes until user saves or clears
        
    Structure:
        {
            'name': 'My Meal',
            'servings': 1,
            'ingredients': [
                {
                    'fdcId': 123,
                    'description': 'Chicken breast',
                    'grams': 200,
                    'nutrients': {'protein': 31, ...}
                },
                ...
            ]
        }
    """
    # Get current meal from session, or create new empty meal
    # session.get() returns None if key doesn't exist, so we provide default
    current_meal = session.get('current_meal', {
        'name': 'My Meal',
        'servings': 1,
        'ingredients': []
    })
    
    # Calculate total nutrition for display
    # calculate_nutrition() is a helper function defined below
    nutrition = calculate_nutrition(current_meal['ingredients'], current_meal['servings'])
    
    # Render template with current meal state
    return render_template('create_meal.html', 
                         meal=current_meal, 
                         nutrition=nutrition)


# ============================================================================
# SEARCH INGREDIENT - Search within meal creation page
# ============================================================================
@app.route('/search-ingredient', methods=['POST'])
def search_ingredient():
    """
    Search for ingredients to add to current meal.
    
    This is like /search but:
        - Happens within the meal creation page
        - Results stay on same page
        - User can click "Add to Meal" buttons
    """
    query = request.form.get('query', '')
    
    # Get current meal state from session
    current_meal = session.get('current_meal', {
        'name': 'My Meal',
        'servings': 1,
        'ingredients': []
    })
    
    try:
        # Call backend search API
        response = requests.get(f'{BACKEND_URL}/api/search', params={'query': query})
        results = response.json()
        
        # Calculate current nutrition
        nutrition = calculate_nutrition(current_meal['ingredients'], current_meal['servings'])
        
        # Render same page with search results added
        return render_template('create_meal.html', 
                             meal=current_meal,
                             search_results=results.get('foods', []),
                             query=query,
                             nutrition=nutrition)
    except Exception as e:
        return render_template('error.html', error=str(e))


# ============================================================================
# ADD INGREDIENT - Add ingredient to meal being built
# ============================================================================
@app.route('/add-ingredient', methods=['POST'])
def add_ingredient():
    """
    Add an ingredient to the current meal in session.
    
    Form Data (hidden fields from search results):
        - fdcId: USDA food ID
        - description: Food name
        - brandName: Brand (if any)
        - protein, fat, carbs, calories: Nutrient values per 100g
        - grams: User-specified amount (user can change from default 100g)
    """
    # Get current meal from session
    current_meal = session.get('current_meal', {
        'name': 'My Meal',
        'servings': 1,
        'ingredients': []
    })
    
    # Build ingredient object from form data
    # request.form.get() safely gets form field (returns None if missing)
    ingredient = {
        'fdcId': int(request.form.get('fdcId')),
        'description': request.form.get('description'),
        'brandName': request.form.get('brandName', ''),
        'grams': float(request.form.get('grams', 100)),
        'nutrients': {
            'protein': float(request.form.get('protein', 0)),
            'fat': float(request.form.get('fat', 0)),
            'carbs': float(request.form.get('carbs', 0)),
            'calories': float(request.form.get('calories', 0))
        }
    }
    
    # Add to ingredients list
    current_meal['ingredients'].append(ingredient)
    
    # Save updated meal back to session
    # This updates the encrypted cookie in browser
    session['current_meal'] = current_meal
    
    # Redirect back to meal creation page
    # redirect() sends HTTP 302 to browser, browser requests new URL
    # url_for('create_meal_page') generates /create-meal
    return redirect(url_for('create_meal_page'))


# ============================================================================
# REMOVE INGREDIENT - Remove ingredient from meal
# ============================================================================
@app.route('/remove-ingredient/<int:index>', methods=['POST'])
def remove_ingredient(index):
    """
    Remove an ingredient from current meal by array index.
    
    Path Parameters:
        index (int): Position in ingredients array (0-based)
        
    Example:
        POST /remove-ingredient/1
        → Removes second ingredient (index 1)
    """
    current_meal = session.get('current_meal', {
        'name': 'My Meal',
        'servings': 1,
        'ingredients': []
    })
    
    # Safety check: only remove if index is valid
    # Prevents IndexError if user somehow sends invalid index
    if 0 <= index < len(current_meal['ingredients']):
        current_meal['ingredients'].pop(index)  # Remove item at position
    
    # Save updated meal to session
    session['current_meal'] = current_meal
    
    return redirect(url_for('create_meal_page'))


# ============================================================================
# UPDATE MEAL INFO - Change meal name and servings
# ============================================================================
@app.route('/update-meal-info', methods=['POST'])
def update_meal_info():
    """
    Update meal name and number of servings.
    
    Form Data:
        name: Meal name (string)
        servings: Number of servings (integer)
    """
    current_meal = session.get('current_meal', {
        'name': 'My Meal',
        'servings': 1,
        'ingredients': []
    })
    
    # Update fields from form
    current_meal['name'] = request.form.get('name', 'My Meal')
    current_meal['servings'] = int(request.form.get('servings', 1))
    
    # Save to session
    session['current_meal'] = current_meal
    
    return redirect(url_for('create_meal_page'))


# ============================================================================
# SAVE MEAL - Persist meal to database via backend API
# ============================================================================
@app.route('/save-meal', methods=['POST'])
def save_meal():
    """
    Save completed meal to database.
    
    Flow:
        1. Get current meal from session
        2. Calculate final nutrition
        3. Send to backend API (POST /api/meals)
        4. Backend saves to PostgreSQL
        5. Clear session (meal is saved, start fresh)
        6. Redirect to meals list
    """
    current_meal = session.get('current_meal', {
        'name': 'My Meal',
        'servings': 1,
        'ingredients': []
    })
    
    # Validate: must have at least one ingredient
    if not current_meal['ingredients']:
        return render_template('error.html', error='No ingredients added to meal!')
    
    # Calculate final nutrition values
    nutrition = calculate_nutrition(current_meal['ingredients'], current_meal['servings'])
    
    # Prepare data for backend API
    # Backend expects specific JSON structure
    meal_data = {
        'name': current_meal['name'],
        'servings': current_meal['servings'],
        'ingredients': current_meal['ingredients'],
        'nutritionTotal': nutrition['total'],
        'nutritionPerServing': nutrition['perServing']
    }
    
    try:
        # POST to backend API
        response = requests.post(f'{BACKEND_URL}/api/meals', json=meal_data)
        
        if response.ok:
            # Success! Clear the session (meal is saved)
            session.pop('current_meal', None)
            
            # Redirect to meals list to see saved meal
            return redirect(url_for('meals'))
        else:
            return render_template('error.html', error='Error saving meal to backend')
            
    except Exception as e:
        return render_template('error.html', error=str(e))


# ============================================================================
# CLEAR MEAL - Reset current meal
# ============================================================================
@app.route('/clear-meal', methods=['POST'])
def clear_meal():
    """
    Clear current meal being built (start over).
    
    Removes 'current_meal' from session.
    Next page load will create new empty meal.
    """
    session.pop('current_meal', None)
    return redirect(url_for('create_meal_page'))


# ============================================================================
# VIEW MEALS - Show all saved meals
# ============================================================================
@app.route('/meals')
def meals():
    """
    Display list of all saved meals from database.
    
    Flow:
        1. Call backend API (GET /api/meals)
        2. Backend queries PostgreSQL
        3. Render meals.html with data
    """
    try:
        # Get meals from backend
        response = requests.get(f'{BACKEND_URL}/api/meals')
        data = response.json()
        
        # Render template with meals data
        return render_template('meals.html', meals=data.get('meals', []))
        
    except Exception as e:
        return render_template('error.html', error=str(e))


# ============================================================================
# DELETE MEAL - Remove meal from database
# ============================================================================
@app.route('/meals/delete/<int:meal_id>', methods=['POST'])
def delete_meal(meal_id):
    """
    Delete a saved meal.
    
    Path Parameters:
        meal_id (int): Database ID of meal to delete
        
    Flow:
        1. Send DELETE request to backend
        2. Backend removes from PostgreSQL
        3. Redirect back to meals list
    """
    try:
        # DELETE to backend API
        requests.delete(f'{BACKEND_URL}/api/meals/{meal_id}')
        
        # Redirect to meals list (meal will be gone)
        return redirect(url_for('meals'))
        
    except Exception as e:
        return render_template('error.html', error=str(e))


# ============================================================================
# HELPER FUNCTION - Calculate Nutrition Totals
# ============================================================================
def calculate_nutrition(ingredients, servings):
    """
    Calculate total and per-serving nutrition for a list of ingredients.
    
    Args:
        ingredients (list): Array of ingredient dicts
        servings (int): Number of servings
        
    Returns:
        dict: {
            'total': {protein, fat, carbs, calories},
            'perServing': {protein, fat, carbs, calories}
        }
        
    Math:
        USDA values are "per 100g"
        If ingredient is 200g with 31g protein per 100g:
            Actual protein = (200/100) * 31 = 62g
        
        Sum all ingredients = total
        Divide by servings = per serving
    """
    totals = {
        'protein': 0,
        'fat': 0,
        'carbs': 0,
        'calories': 0
    }
    
    # Sum nutrition from all ingredients
    for ing in ingredients:
        # Calculate multiplier (200g = factor of 2.0)
        factor = ing['grams'] / 100
        
        # Multiply USDA values (per 100g) by factor
        totals['protein'] += ing['nutrients']['protein'] * factor
        totals['fat'] += ing['nutrients']['fat'] * factor
        totals['carbs'] += ing['nutrients']['carbs'] * factor
        totals['calories'] += ing['nutrients']['calories'] * factor
    
    # Calculate per-serving values
    per_serving = {
        'protein': round(totals['protein'] / servings, 2),
        'fat': round(totals['fat'] / servings, 2),
        'carbs': round(totals['carbs'] / servings, 2),
        'calories': round(totals['calories'] / servings, 2)
    }
    
    return {
        'total': {
            'protein': round(totals['protein'], 2),
            'fat': round(totals['fat'], 2),
            'carbs': round(totals['carbs'], 2),
            'calories': round(totals['calories'], 2)
        },
        'perServing': per_serving
    }


# ============================================================================
# HEALTH CHECK - For Kubernetes probes
# ============================================================================
@app.route('/health')
def health():
    """
    Health check endpoint for Kubernetes liveness/readiness probes.
    
    Kubernetes periodically checks this endpoint.
    If it fails, Kubernetes restarts the pod.
    """
    return {'status': 'healthy', 'service': 'meal-prep-frontend'}, 200


# ============================================================================
# APPLICATION STARTUP
# ============================================================================
if __name__ == '__main__':
    # Get port from environment variable (Kubernetes sets this)
    port = int(os.getenv('PORT', 3000))
    
    # Start Flask development server
    # host='0.0.0.0' allows external connections (required for Docker/Kubernetes)
    # debug=True enables auto-reload and detailed error pages
    app.run(host='0.0.0.0', port=port, debug=True)
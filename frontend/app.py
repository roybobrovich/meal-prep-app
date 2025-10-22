from flask import Flask, render_template, request, redirect, url_for, session
import requests
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Backend API URL
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    """Search for food"""
    if request.method == 'POST':
        query = request.form.get('query', '')
        
        try:
            response = requests.get(f'{BACKEND_URL}/api/search', params={'query': query})
            results = response.json()
            return render_template('search_results.html', 
                                 foods=results.get('foods', []), 
                                 query=query)
        except Exception as e:
            return render_template('error.html', error=str(e))
    
    return render_template('search.html')

@app.route('/create-meal', methods=['GET'])
def create_meal_page():
    """Create meal page - shows current meal being built"""
    # Get current meal from session
    current_meal = session.get('current_meal', {
        'name': 'My Meal',
        'servings': 1,
        'ingredients': []
    })
    
    # Calculate nutrition
    nutrition = calculate_nutrition(current_meal['ingredients'], current_meal['servings'])
    
    return render_template('create_meal.html', 
                         meal=current_meal, 
                         nutrition=nutrition)

@app.route('/search-ingredient', methods=['POST'])
def search_ingredient():
    """Search for ingredient to add to meal"""
    query = request.form.get('query', '')
    
    # Get current meal from session
    current_meal = session.get('current_meal', {
        'name': 'My Meal',
        'servings': 1,
        'ingredients': []
    })
    
    try:
        response = requests.get(f'{BACKEND_URL}/api/search', params={'query': query})
        results = response.json()
        
        nutrition = calculate_nutrition(current_meal['ingredients'], current_meal['servings'])
        
        return render_template('create_meal.html', 
                             meal=current_meal,
                             search_results=results.get('foods', []),
                             query=query,
                             nutrition=nutrition)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/add-ingredient', methods=['POST'])
def add_ingredient():
    """Add ingredient to current meal"""
    # Get current meal from session
    current_meal = session.get('current_meal', {
        'name': 'My Meal',
        'servings': 1,
        'ingredients': []
    })
    
    # Get ingredient data from form
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
    
    # Save back to session
    session['current_meal'] = current_meal
    
    return redirect(url_for('create_meal_page'))

@app.route('/remove-ingredient/<int:index>', methods=['POST'])
def remove_ingredient(index):
    """Remove ingredient from current meal"""
    current_meal = session.get('current_meal', {
        'name': 'My Meal',
        'servings': 1,
        'ingredients': []
    })
    
    if 0 <= index < len(current_meal['ingredients']):
        current_meal['ingredients'].pop(index)
    
    session['current_meal'] = current_meal
    
    return redirect(url_for('create_meal_page'))

@app.route('/update-meal-info', methods=['POST'])
def update_meal_info():
    """Update meal name and servings"""
    current_meal = session.get('current_meal', {
        'name': 'My Meal',
        'servings': 1,
        'ingredients': []
    })
    
    current_meal['name'] = request.form.get('name', 'My Meal')
    current_meal['servings'] = int(request.form.get('servings', 1))
    
    session['current_meal'] = current_meal
    
    return redirect(url_for('create_meal_page'))

@app.route('/save-meal', methods=['POST'])
def save_meal():
    """Save meal to database"""
    current_meal = session.get('current_meal', {
        'name': 'My Meal',
        'servings': 1,
        'ingredients': []
    })
    
    if not current_meal['ingredients']:
        return render_template('error.html', error='No ingredients added to meal!')
    
    # Calculate nutrition
    nutrition = calculate_nutrition(current_meal['ingredients'], current_meal['servings'])
    
    # Prepare meal data for API
    meal_data = {
        'name': current_meal['name'],
        'servings': current_meal['servings'],
        'ingredients': current_meal['ingredients'],
        'nutritionTotal': nutrition['total'],
        'nutritionPerServing': nutrition['perServing']
    }
    
    try:
        response = requests.post(f'{BACKEND_URL}/api/meals', json=meal_data)
        
        if response.ok:
            # Clear current meal from session
            session.pop('current_meal', None)
            return redirect(url_for('meals'))
        else:
            return render_template('error.html', error='Error saving meal to backend')
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/clear-meal', methods=['POST'])
def clear_meal():
    """Clear current meal"""
    session.pop('current_meal', None)
    return redirect(url_for('create_meal_page'))

@app.route('/meals')
def meals():
    """View saved meals"""
    try:
        response = requests.get(f'{BACKEND_URL}/api/meals')
        data = response.json()
        return render_template('meals.html', meals=data.get('meals', []))
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/meals/delete/<int:meal_id>', methods=['POST'])
def delete_meal(meal_id):
    """Delete a meal"""
    try:
        requests.delete(f'{BACKEND_URL}/api/meals/{meal_id}')
        return redirect(url_for('meals'))
    except Exception as e:
        return render_template('error.html', error=str(e))

def calculate_nutrition(ingredients, servings):
    """Calculate total and per-serving nutrition"""
    totals = {
        'protein': 0,
        'fat': 0,
        'carbs': 0,
        'calories': 0
    }
    
    for ing in ingredients:
        factor = ing['grams'] / 100  # USDA values are per 100g
        totals['protein'] += ing['nutrients']['protein'] * factor
        totals['fat'] += ing['nutrients']['fat'] * factor
        totals['carbs'] += ing['nutrients']['carbs'] * factor
        totals['calories'] += ing['nutrients']['calories'] * factor
    
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

@app.route('/health')
def health():
    """Health check"""
    return {'status': 'healthy', 'service': 'meal-prep-frontend'}, 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=True)
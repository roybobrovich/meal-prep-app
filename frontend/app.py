from flask import Flask, render_template, request, redirect, url_for
import requests
import os

app = Flask(__name__)

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

@app.route('/health')
def health():
    """Health check"""
    return {'status': 'healthy', 'service': 'meal-prep-frontend'}, 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=True)
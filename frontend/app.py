from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import os

app = Flask(__name__)
# To be Changes 
app.secret_key = 'dev-key-123-abc!@#'

DATABASE_URL = os.getenv('DATABASE_URL', 'http://database:5003')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # Call database service to verify credentials
            response = requests.post(f"{DATABASE_URL}/login", json={
                'email': email,
                'password': password
            })
            
            if response.status_code == 200:
                data = response.json()
                session['user_id'] = data.get('user_id')
                session['user_type'] = data.get('user_type')
                session['email'] = email
                
                # Redirect based on user type
                if data.get('user_type') == 'hr':
                    return redirect(url_for('hr_dashboard'))
                elif data.get('user_type') == 'company':
                    return redirect(url_for('company_dashboard'))
                else:
                    return redirect(url_for('jobseeker_dashboard'))
            else:
                flash('Invalid email or password', 'error')
        except Exception as e:
            flash('Connection error: ' + str(e), 'error')
        
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone_number')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        user_type = request.form.get('user_type')  # Add this field to your form
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))
        
        try:
            # Call database service to create user
            response = requests.post(f"{DATABASE_URL}/signup", json={
                'full_name': full_name,
                'email': email,
                'phone_number': phone,
                'password': password,
                'user_type': user_type
            })
            
            if response.status_code == 201:
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                flash(response.json().get('message', 'Registration failed'), 'error')
        except Exception as e:
            flash('Connection error: ' + str(e), 'error')
        
        return redirect(url_for('signup'))
    
    return render_template('signup.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 
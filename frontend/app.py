from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import os

app = Flask(__name__)
# To be Changes 
app.secret_key = 'dev-key-123-abc!@#'

DATABASE_URL = os.getenv('DATABASE_URL', 'http://database:5003')


# Main Dashboard
@app.route('/')
def index():
    return render_template('index.html')

# Login & Signup
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

# Jobseeker Dashboard 
@app.route('/upload_cv', methods=['GET', 'POST'])
def upload_cv():
    # if 'user_id' not in session:
    #     flash('Please login first', 'error')
    #     return redirect(url_for('login'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Send file to CV extraction service
                files = {'file': (file.filename, file.stream, file.mimetype)}
                response = requests.post(
                    "http://cv-extraction:5001/extract-cv",
                    files=files
                )
                
                if response.status_code == 200:
                    cv_data = response.json().get('cv_data', {})
                    
                    # Save to database with user_id
                    # save csv info using user id
                    save_response = requests.post(
                        f"{DATABASE_URL}/add_application",
                        json={
                            'cv_data': cv_data,
                            'user_id': session['user_id']
                        }
                    )
                    
                    if save_response.status_code == 201:
                        flash('CV uploaded and processed successfully!', 'success')
                        return redirect(url_for('jobseeker_dashboard'))
                    else:
                        flash('Error saving CV data', 'error')
                else:
                    flash('Error processing CV', 'error')
            except Exception as e:
                flash(f'Error: {str(e)}', 'error')
        
        return redirect(request.url)
    
    return render_template('upload_cv.html')

@app.route('/profile')
def jobseeker_profile():
    # if 'user_id' not in session:
    #     flash('Please login first', 'error')
    #     return redirect(url_for('login'))
    
    # try:
    #     # Get user info from database API
    #     user_response = requests.get(f"{DATABASE_URL}/get_user_info/{session['user_id']}")
    #     if user_response.status_code != 200:
    #         flash('Error fetching user data', 'error')
    #         return redirect(url_for('jobseeker_dashboard'))
        
    #     user_data = user_response.json().get('user', {})
        
    #     # Get application info if exists
    #     application_response = requests.get(
    #         f"{DATABASE_URL}/get_applications?user_id={session['user_id']}"
    #     )
    #     application_data = {}
    #     if application_response.status_code == 200:
    #         applications = application_response.json().get('applications', [])
    #         if applications:
    #             application_data = applications[0]  # Get most recent application
        
    #     return render_template('profile.html', 
    #                         user=user_data, 
    #                         application=application_data)
    
    # except Exception as e:
    #     flash(f'Error loading profile: {str(e)}', 'error')
    #     return redirect(url_for('jobseeker_dashboard'))
    sample_user = {
        'full_name': 'John Doe',
        'email': 'john.doe@example.com'
    }
    
    # Sample application data (matches your template structure)
    sample_application = {
        'skills': ['Python', 'Flask', 'HTML/CSS', 'JavaScript'],
        'exp_years': 5,
        'phone_number': '+1 (555) 123-4567',
        'education': [
            {
                'degree': 'B.Sc Computer Science',
                'institution': 'State University'
            }
        ],
        'experience': [
            {
                'role': 'Senior Developer',
                'company': 'Tech Solutions Inc.',
                'responsibilities': 'Led a team of developers building web applications'
            },
            {
                'role': 'Software Engineer',
                'company': 'Digital Creations',
                'responsibilities': 'Developed backend services and APIs'
            }
        ]
    }
    
    return render_template(
        'profile.html', 
        user=sample_user, 
        application=sample_application
    )
@app.route('/jobseeker_dashboard', methods=['GET', 'POST'])
def jobseeker_dashboard():
    # if 'user_id' not in session:
    #     flash('Please login first', 'error')
    #     return redirect(url_for('login'))
    
    # try:
    #     # Get all jobs from database
    #     response = requests.get(f"{DATABASE_URL}/job")
    #     if response.status_code != 200:
    #         flash('Error fetching jobs', 'error')
    #         return render_template('jobseeker_dashboard.html', jobs=[])
        
    #     jobs = response.json().get('jobs', [])
        
    #     # If user submits an application
    #     if request.method == 'POST':
    #         job_id = request.form.get('job_id')
    #         if job_id:
    #             # Here you would save the application to your database
    #             # You might want to create a new table for applications
    #             application_response = requests.post(
    #                 f"{DATABASE_URL}/apply_job",
    #                 json={
    #                     'user_id': session['user_id'],
    #                     'job_id': job_id,
    #                     'status': 'applied'
    #                 }
    #             )
                
    #             if application_response.status_code == 201:
    #                 flash('Application submitted successfully!', 'success')
    #             else:
    #                 flash('Error submitting application', 'error')
                
    #             return redirect(url_for('jobseeker_dashboard'))
        
    #     return render_template('jobseeker_dashboard.html', jobs=jobs)
    
    # except Exception as e:
    #     flash(f'Error loading dashboard: {str(e)}', 'error')
    #     return render_template('jobseeker_dashboard.html', jobs=[])

    jobs_data = {
        "jobs": [
            {
                "id": 1,
                "title": "Senior Python Developer",
                "description": "Develop and maintain backend services using Python and Flask",
                "company_id": 1,
                "job_level": "Senior",
                "years_experience": "5",
                "responsibilities": [
                    "Design and implement RESTful APIs",
                    "Optimize application performance",
                    "Mentor junior developers"
                ],
                "requirements": [
                    "5+ years Python experience",
                    "Experience with Flask/Django",
                    "Knowledge of PostgreSQL"
                ],
                "created_at": "2023-05-15T10:30:00",
                "company": {
                    "id": 1,
                    "full_name": "TechCorp Inc."
                }
            },
            {
                "id": 2,
                "title": "Frontend Engineer",
                "description": "Build responsive user interfaces with React",
                "company_id": 2,
                "job_level": "Mid-level",
                "years_experience": "3",
                "responsibilities": [
                    "Develop new user-facing features",
                    "Build reusable components",
                    "Optimize for maximum performance"
                ],
                "requirements": [
                    "3+ years JavaScript experience",
                    "Proficient with React",
                    "Experience with Redux"
                ],
                "created_at": "2023-05-10T09:15:00",
                "company": {
                    "id": 2,
                    "full_name": "WebSolutions Ltd."
                }
            }
        ]
    }
    
    # Pass just the jobs list to the template, not the whole dictionary
    return render_template('jobseeker_dashboard.html', jobs=jobs_data["jobs"])
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 
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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['pdf']


@app.route('/jobseeker_dashboard')
def jobseeker_dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    return render_template('jobseeker_dashboard.html')

@app.route('/company_dashboard')
def company_dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    return render_template('company_dashboard.html')

@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            # Get form data
            form_data = request.form
            company_id = session.get('user_id')  # Get company ID from session
            
            # Prepare data for job generator
            job_data = {
                'job_title': form_data.get('jobTitle'),
                'job_level': form_data.get('jobLevel'),
                'years_experience': form_data.get('yearsExperience'),
                'company_id': company_id
            }

            # Validate required fields
            required_fields = ['job_title', 'job_level', 'years_experience', 'company_id']
            if not all(job_data[field] for field in required_fields):
                flash('Please fill all required fields', 'error')
                return redirect(url_for('post_job'))

            # Call job generator service
            generator_response = requests.post(
                "http://job-generator:6000/generate-job-description",
                json=job_data,
                timeout=10
            )

            if generator_response.status_code != 200:
                flash('Failed to generate job description', 'error')
                return redirect(url_for('post_job'))

            generated_data = generator_response.json().get('job_description', {})
            
            # Prepare data for database
            db_payload = {
                'title': generated_data.get('job_title', job_data['job_title']),
                'description': job_data['additional_info'],
                'company_id': job_data['company_id'],
                'job_level': generated_data.get('job_level', job_data['job_level']),
                'years_experience': generated_data.get('years_experience', job_data['years_experience']),
                'responsibilities': generated_data.get('responsibilities', []),
                'requirements': generated_data.get('requirements', []),
                'required_certifications': generated_data.get('required_certifications', [])
            }

            # Save to database
            db_response = requests.post(
                "http://backend:5003/jobs",
                json=db_payload,
                timeout=5
            )

            if db_response.status_code == 201:
                job_id = db_response.json().get('job_id')
                flash('Job posted successfully!', 'success')
                return redirect(url_for('view_job', job_id=job_id))
            else:
                error_msg = db_response.json().get('message', 'Failed to save job')
                flash(f'Database error: {error_msg}', 'error')

        except requests.exceptions.RequestException as e:
            flash(f'Service error: {str(e)}', 'error')
        except Exception as e:
            flash(f'Unexpected error: {str(e)}', 'error')

        return redirect(url_for('post_job'))

    # GET request - show the form
    return render_template('post_job.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 
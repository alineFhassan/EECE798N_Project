from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
import requests
import os
from datetime import datetime
from flask_mail import Mail, Message
import re
import logging
from prometheus_client import Counter, Histogram, generate_latest
import time

app = Flask(__name__)
# ========================
#   Prometheus metrics
# ========================
UPLOAD_CV_COUNT = Counter('upload_cv_requests_total', 'Total /upload_cv requests')
UPLOAD_CV_SUCCESS = Counter('upload_cv_success_total', 'Total successful CV uploads')
UPLOAD_CV_FAILURE = Counter('upload_cv_failure_total', 'Total failed CV uploads')
UPLOAD_CV_TIME = Histogram('upload_cv_processing_seconds', 'Time spent in upload_cv')

# ========================
#   CONFIGURE FLASK-MAIL
# ========================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
# Replace with your Gmail credentials
app.config['MAIL_USERNAME'] = 'zynab.ahmad.saad@gmail.com' 
app.config['MAIL_DEFAULT_SENDER'] = 'zynab.ahmad.saad@gmail.com' 
app.config['MAIL_PASSWORD'] = 'teyv eues tgoq ipvt'  
mail = Mail(app)

# ===========================================
#   SECRET KEY FOR SESSION MANAGEMENT
# ===========================================
app.secret_key = 'dev-key-123-abc!@#'

BACKEND_API_URL = "http://backend:5000"
CV_EXTRACTION_URL="http://cv-extraction-api:3001"
JOB_DESCRIPTION_URL="http://job-description-api:3002" 
CV_JOB_MATCHING_URL="http://cv-job-matching-api:3003"
INTERVIEW_QUESTIONS_URL= "http://interview-questions-api:3004"
ANSWER_EVALUATION_URL= "http://answer-evaluation-api:3005"
# ========================
#  MAIN APPLICATION ENTRY
# ========================
@app.route('/')
def index():
    return render_template('index.html')

# ===========================================
#       LOGIN LOGOUT SIGNUP
# ===========================================

# ========================
#   LOGIN
# ========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password')
        register_option = request.form.get('user_type')
        
        # Validate inputs
        if not email or not password or not register_option:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('login'))
        
        if not validate_email_format(email):
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('login'))
    
        try:
            # Verifying Credentials 
            auth_response = requests.post(f"{BACKEND_API_URL}/login", json={
                    'email': email,
                    'password': password,
                    'register_option': register_option
                } ) 
                
            if auth_response.status_code == 200:
                    data = auth_response.json()
                    session['user_id'] = data.get('user_id')
                    session['register_option'] = data.get('register_option')
                    session['email'] = email
                    
                     # Redirect based on user type (consider using a mapping)
                    if data.get('register_option') == 'company':
                        if session['user_id'] == 1:
                            return redirect(url_for('offered_job'))
                        else:
                            return redirect(url_for('company_dashboard'))
                    
                    return redirect(url_for('jobseeker_dashboard'))
            else:
                # Generic error message to prevent information disclosure
                flash('Login failed. Please check your credentials and try again', 'error')
                    
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Login connection error: {str(e)}")
            flash('Service temporarily unavailable. Please try again later', 'error')
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            flash('An unexpected error occurred during login', 'error')
        return redirect(url_for('login')) 
    return render_template('login.html')

# Function To Validate email
def validate_email_format(email):
    """Basic email format validation"""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

# ========================
#  SIGNUP
# ========================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # 1. Stronger Input Validation
        first_name = request.form.get('first_name','').strip()
        last_name = request.form.get('last_name','').strip()
        email = request.form.get('email','').strip()
        phone = request.form.get('phone_number','').strip()
        date_str = request.form.get('dob','').strip()
        password = request.form.get('password','').strip()
        confirm_password = request.form.get('confirm_password','').strip()
        
        # 2. Better Password Validation
        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return redirect(url_for('signup'))
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))
        
        # 3. Email Validation
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email address', 'error')
            return redirect(url_for('signup'))
            
        # 4. Phone Number Validation (basic)
        if not phone.isdigit() or len(phone) < 10:
            flash('Invalid phone number', 'error')
            return redirect(url_for('signup'))
        
        # 5. Check for empty fields after cleaning
        if not all([first_name, last_name, email, phone, date_str, password]):
            flash('All fields are required', 'error')
            return redirect(url_for('signup'))
        
        try:
            # Call database service to create user
            response = requests.post(f"{BACKEND_API_URL}/signup", json={
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'date':date_str,
                'phone_number': phone,
                'password': password
            }, )
            
            if response.status_code == 201:
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                try:
                    error_msg = response.json().get('message', 'Registration failed')
                    flash(error_msg, 'error')
                except ValueError:
                    flash('Registration failed - server error', 'error')
        except requests.exceptions.RequestException as e:
            flash('Service temporarily unavailable. Please try again later.', 'error')
            app.logger.error(f"Signup API error: {str(e)}")
        except Exception as e:
            flash('An unexpected error occurred', 'error')
            app.logger.exception("Unexpected signup error")
        
        return redirect(url_for('signup'))
    
    return render_template('signup.html')

# ========================
#   LOGOUT
# ========================
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    try:
        # Clear the session data
        session.clear()
        
        # Create a response with the index page
        response = make_response(redirect(url_for('index')))  # Redirect to index page
        
        # Add headers to prevent caching of the protected pages
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        
        # Add security headers to prevent going back
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ===========================================
#       PROMETHEUS MONITORING
# ===========================================
@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/monitoring_dashboard')
def monitoring_dashboard():
    return render_template('monitoring_dashboard.html')


# ===========================================
#       APPLICANR DASHBOARD CONFIGURATION
# ===========================================
# -------- CONFIGURATION FOR ALLOWED FILES --------
ALLOWED_EXTENSIONS = {'pdf'} # alowed extension
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB limit

# -------- FUNCTION FOR ALLOWED FILES --------
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ========================
#   UPLOAD CV
# ========================  
@app.route('/upload_cv', methods=['GET', 'POST'])
def upload_cv():
    UPLOAD_CV_COUNT.inc()  # Increment total request count

    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('jobseeker_dashboard'))
    
    # Initialize has_cv as False by default
    has_cv = False
    
    # Check if user has CV (for displaying upload prompt)
    cv_check = requests.get(f"{BACKEND_API_URL}/check_cv_exists/{session['user_id']}")
    if cv_check.status_code == 200:
        has_cv = cv_check.json().get('cv_exists', False)

    # Handle POST requests (file upload) regardless of whether CV exists
    if request.method == 'POST':
        # If CV exists and user is trying to upload again, you might want to handle differently
        if has_cv:
            flash('You already have a CV uploaded. Contact support to replace it.', 'info')
            return redirect(url_for('jobseeker_dashboard'))
            
        start_time = time.time()
        try:
            if 'pdfFile' not in request.files:
                flash('No file selected', 'error')
                return redirect(url_for('upload_cv'))  # Redirect back to upload page

            file = request.files['pdfFile'] 

            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(url_for('upload_cv'))
            
            if not (file and allowed_file(file.filename)):
                flash('Invalid file type. Only PDF/DOCX files are allowed', 'error')
                return redirect(url_for('upload_cv'))
            
            files = {'file': (file.filename, file.stream, file.mimetype)}
            response = requests.post(f"{CV_EXTRACTION_URL}/extract-cv", files=files)
            response.raise_for_status()

            cv_data = response.json().get('cv_data', {})
                                  
            if not cv_data.get('skills') or not cv_data.get('experience'):
                flash('CV processed but missing critical data (skills/experience)', 'warning')
            
            save_response = requests.post(
                f"{BACKEND_API_URL}/add_applicant",
                json={'cv_data': cv_data, 'user_id': session['user_id']}
            )
            
            if save_response.status_code == 201:
                flash('CV uploaded and processed successfully!', 'success')
                UPLOAD_CV_SUCCESS.inc()
                return redirect(url_for('jobseeker_dashboard'))
            
            flash(save_response.json().get('message', 'Error saving CV data'), 'error')
            UPLOAD_CV_FAILURE.inc()

        except requests.exceptions.RequestException as e:
            flash('CV processing service unavailable. Please try later.', 'error')
            app.logger.error(f"CV processing error: {str(e)}")
            UPLOAD_CV_FAILURE.inc()
        except Exception as e:
            flash('An unexpected error occurred', 'error')
            app.logger.exception("CV upload error")
            UPLOAD_CV_FAILURE.inc()
        finally:
            elapsed = time.time() - start_time
            UPLOAD_CV_TIME.observe(elapsed)

    # Always render the template with current has_cv status
    return render_template('upload_cv.html', has_cv=has_cv)
# ========================
#   APPLICANR PROFILE
# ========================  
@app.route('/profile')
def jobseeker_profile():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    try:
       # Get user info
        user_response = requests.get(f"{BACKEND_API_URL}/get_user/{session['user_id']}")
        user_response.raise_for_status()

        user_data = user_response.json().get('user', {})
        
        # Get application info
        app_response = requests.get(
            f"{BACKEND_API_URL}/get_applicant/{session['user_id']}"
        )
        application_data = {}
        if app_response.status_code == 200:
            application_data = app_response.json().get('cv_data', {})
        elif app_response.status_code != 404:
            app_response.raise_for_status()
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        logger.debug(f"app: {application_data}")
        return render_template(
            'profile.html', 
            user=user_data, 
            application=application_data
        )
    
    except requests.exceptions.HTTPError as e:
        flash('Error fetching profile data from server', 'error')
        app.logger.error(f"Profile data fetch error: {str(e)}")
    except Exception as e:
        flash('Failed to load profile', 'error')
        app.logger.exception("Profile load error")
    
    return redirect(url_for('jobseeker_dashboard'))

# ========================
#   JOBSEEKER DASHBOARD
# ========================  
@app.route('/jobseeker_dashboard', methods=['GET', 'POST'])
def jobseeker_dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    try:
        # Get all jobs from database
        response = requests.get(f"{BACKEND_API_URL}/get_offered_job")
        if response.status_code != 200:
            flash('Error fetching jobs', 'error')
            return render_template('jobseeker_dashboard.html', jobs=[])
        
        jobs = response.json().get('jobs', [])

        # Filter only open jobs
        open_jobs = [job for job in jobs if job.get('status', '').lower() == 'open']

        # Add this loop after fetching open_jobs
        for job in open_jobs:
            job_id = job.get('id')
            applied_response = requests.get(f"{BACKEND_API_URL}/check_if_applied/{session['user_id']}/{job_id}")
            if applied_response.status_code == 200:
                job['already_applied'] = applied_response.json().get('already_applied', False)
            else:
                job['already_applied'] = False  # Assume not applied on error


        # Handle job application
        if request.method == 'POST':
            # Check if user has uploaded CV
            cv_check = requests.get(f"{BACKEND_API_URL}/check_cv_exists/{session['user_id']}")
            if cv_check.status_code != 200 or not cv_check.json().get('cv_exists', False):
                flash('Please upload your CV before applying for jobs', 'error')
                return redirect(url_for('upload_cv'))

            job_id = request.form.get('job_id')
            if not job_id:
                flash('No job selected', 'error')
                return redirect(url_for('jobseeker_dashboard'))

            # Get job details
            job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{job_id}")
            if job_response.status_code != 200:
                flash('Error fetching job details', 'error')
                return redirect(url_for('jobseeker_dashboard'))
            
            job_data = job_response.json().get('job', {})
            
            if job_data.get('status', '').lower() != 'open':
                flash('This job is no longer available', 'error')
                return redirect(url_for('jobseeker_dashboard'))

            # Get CV data
            cv_response = requests.get(f"{BACKEND_API_URL}/get_applicant/{session['user_id']}")
            if cv_response.status_code != 200:
                flash('Error fetching your CV', 'error')
                return redirect(url_for('jobseeker_dashboard'))

            cv_data = cv_response.json().get('cv_data', {})

            # Match CV with job (optional step)
            match_result = {}
            if CV_JOB_MATCHING_URL:
                match_response = requests.post(
                    f"{CV_JOB_MATCHING_URL}/cv-job-match",
                    json={'cv': cv_data, 'job': job_data}
                )
                if match_response.status_code == 200:
                    match_result = match_response.json().get('result', {})
                else:
                    flash('Could not evaluate your CV against the job requirements', 'warning')

            # Save application
            application_response = requests.post(
                f"{BACKEND_API_URL}/add_applied_job",
                json={
                    'applicant_id': session['user_id'],
                    'job_id': job_id,
                    'status': 'pending',
                    "result": match_result
                }
            )
            
            if application_response.status_code == 201:
                flash('Application submitted successfully!', 'success')
            else:
                flash('Error submitting application', 'error')
            
            return redirect(url_for('jobseeker_dashboard'))
        
        # Check if user has CV (for displaying upload prompt)
        cv_exists = requests.get(f"{BACKEND_API_URL}/check_cv_exists/{session['user_id']}")
        has_cv = cv_exists.status_code == 200 and cv_exists.json().get('cv_exists', False)
        
        return render_template('jobseeker_dashboard.html', jobs=open_jobs, has_cv=has_cv)
    
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('jobseeker_dashboard.html', jobs=[])

# ===========================================
#       DEPARTMENT DASHBOARD CONFIGURATION
# ===========================================

# ========================
#  DEPARTMENT DASHBOARD
# ========================
@app.route('/company_dashboard')
def company_dashboard():
    if 'user_id' not in session:
        flash('Please login', 'error')
        return redirect(url_for('login'))
    
    try:
        dept_id = session['user_id']
        job_offer_response = requests.get(f"{BACKEND_API_URL}/get_offered_job_by_dept/{dept_id}")
        
        if job_offer_response.status_code != 200:
            flash('Error fetching your company jobs', 'error')
            return render_template('company_dashboard.html', jobs=[], stats={})
        
        jobs = job_offer_response.json().get('jobs', [])
        
        # Transform job data to match template expectations
        processed_jobs = []
        for job in jobs:
            processed_job = {
                'id': job.get('id', 0),
                'job_title': job.get('title', ''),
                'job_level': job.get('job_level', ''),
                'years_experience': job.get('years_experience', ''),
                'date_offering': job.get('created_at', ''),
                'status': job.get('status', ''),
             
            }
            processed_jobs.append(processed_job)

        # Calculate Some Statistics To Display
        stats = {
            'total_jobs': len(processed_jobs),
            'open_jobs': sum(1 for job in processed_jobs if job.get('status', '').lower() == 'open'),
            'closed_jobs': sum(1 for job in processed_jobs if job.get('status', '').lower() == 'closed'),
            'total_applicants': sum(job.get('applicant_count', 0) for job in processed_jobs)
        }
        
        return render_template(
            'company_dashboard.html',
            jobs=processed_jobs,
            stats=stats
        )

    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('company_dashboard.html', jobs=[], stats={})
      
# ========================
#   OFFER JOB
# ========================  
@app.route('/post_job', methods=['POST','GET'])
def post_job():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Validate required fields first
            required_fields = ['jobTitle', 'jobLevel', 'yearsExperience','jobDescription']
            if not all(request.form.get(field) for field in required_fields):
                flash('Please fill all required fields', 'error')
                return redirect(url_for('post_job'))
                
            job_data = {
                'job_title': request.form.get('jobTitle'),   
                'department_id': session['user_id'],
                'job_level': request.form.get('jobLevel'),
                'years_experience': request.form.get('yearsExperience'),
                'additional_info': request.form.get('jobDescription'),     
              
            }
              
        except KeyError as e:
            flash(f'Missing key in session or form data: {str(e)}', 'error')
            return redirect(url_for('post_job'))
        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'error')
            app.logger.error(f"Error creating job posting: {str(e)}")
            return redirect(url_for('post_job'))
        get_job_description_responce = requests.post(f"{JOB_DESCRIPTION_URL}/generate-job-description",
                                            json={
                                            'job_title' : job_data['job_title'],
                                            'job_level' : job_data['job_level'],
                                            'years_experience' : job_data['years_experience'],
                                            'additional_info' : job_data['additional_info']   
                                         })

       
        if get_job_description_responce.status_code != 200:
                    flash('Error saving job description', 'error')
                    return redirect(url_for('post_job'))
 
        job_description = get_job_description_responce.json().get('job_description', {})
        add_offer_job_response = requests.post(f"{BACKEND_API_URL}/add_offer_job", json={
                   "job_description" : job_description,
                   "department_id": job_data['department_id']
                })
        if add_offer_job_response.status_code != 201:
                    flash('Error In Saving job Offere', 'error')
                    return redirect(url_for('post_job'))
        
    return render_template('post_job.html')

# ===========================
#   FILTER JOBS BY DEPARTMENT
# ==========================  
@app.route('/job_applicants/<int:job_id>')
def job_applicants(job_id):
    try:
         # First get the job details
         job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{job_id}")
         if job_response.status_code != 200:
             flash('Job not found', 'error')
             return redirect(url_for('company_dashboard'))
            
         job = job_response.json().get('job')

         logging.basicConfig(level=logging.DEBUG)
         logger = logging.getLogger(__name__)
         # Verify this company owns the job
         if job['dept_id'] != session.get('user_id'):
             flash('You can only view applicants for your own jobs', 'error')
             return redirect(url_for('company_dashboard'))
        
         # Get all applications from the database
         applications_response = requests.get(f"{BACKEND_API_URL}/get_applicants/{job_id}")
         print(applications_response)
         if applications_response.status_code != 200:
             flash('Error fetching applications', 'error')
             return render_template('job_applicants.html', job=job, applicants=[])
            
         all_applications = applications_response.json().get('applications', [])
         logger.debug(f"app: {all_applications}")
         # For demo purposes, we'll just return all applications
         # In a real app, you'd want to filter applications that actually applied to this job
         # You would need an "applications" table that links users to jobs they applied for
        
         return render_template('job_applicants.html', 
                              job=job, 
                              applicants=all_applications)
    
    except Exception as e:
         flash(f'Error: {str(e)}', 'error')
         return redirect(url_for('company_dashboard'))

@app.template_filter('format_date')
def format_date_filter(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
        return date_obj.strftime('%b %d, %Y')
    except:
        return date_str

# -------- LIST OF APPLICANT APPLIED TO A JOB--------
# @app.route('/hr_applied_applicant/<int:job_id>')
# def hr_view_applied_applicant(job_id): 
#     # Fetch job details --> requirements 
#     job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{job_id}")
#     if job_response.status_code != 200:
#         flash('Error fetching your offeredt jobs', 'error')
#         return render_template('hr_view_applied_applicant.html', jobs=[])
        
#     job = job_response.json()
    
#     # Fetch applicants for this job --> with his match result
#     applicants_response = requests.get(f"{BACKEND_API_URL}/get_applied_job/{job_id}")
#     if applicants_response.status_code != 200:
#         flash('Error fetching your applicant', 'error')
#         return render_template('hr_view_applied_applicant.html', job=[])
    
#     applicants_data = []
#     for application in applicants_response.json().get("applications", []):
#         # Get applicant details
#         logging.basicConfig(level=logging.DEBUG)
#         logger = logging.getLogger(__name__)
#         logger.debug(f"app: {application}")
#         user_response = requests.get(f"{BACKEND_API_URL}/get_user/{application['applicant_id']}")
#         if user_response.status_code != 200:
#             continue
            
#         user = user_response.json()
#         user_data = user.get('user', {})
#         # Get applicant CV
#         cv_response = requests.get(f"{BACKEND_API_URL}/get_applicant/{application['applicant_id']}")
#         logger.debug(f"Raw CV response: {cv_response}")
#         logger.debug(f"cv_response.json(): {cv_response.json()}")
#         cv_json = cv_response.json()
#         cv = cv_json.get('cv_data') if cv_response.status_code == 200 and cv_json.get('status') == 'success' else None

#         # Get passed_criteria as a string like '1/6'
#         match_score_str = application.get("passed_criteria", "0/0")  # Default to '0/0' if key is missing
#         logger.debug(f"match_score without percent: {match_score_str}")

#         # Split the string into passed and total
#         passed, total = map(int, match_score_str.split("/"))

#         # Calculate the passed_criteria_percent
#         passed_criteria_percent = (passed / total) * 100 if total != 0  # Avoid division by zero

#         # Create the dictionary to include the percentage
#         match_score = {
#             "passed_criteria_percent": round(passed_criteria_percent, 2),  # Rounded to 2 decimal places
#             "passed_criteria": match_score_str  # You can also store the original passed criteria string
#         }

#         logger.debug(f"match_score with percent: {match_score['passed_criteria_percent']}")

#         applicants_data.append({
#             'id': user_data.get('id'),
#             'name': f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}",
#             'similarity_score': match_score["passed_criteria_percent"],
#             'exp_years': cv.get('experience_years', 0) if cv else 0,
#             'email': user_data.get('email'),
#             'phone_number': user_data.get('phone_number'),
#             'skills': cv.get('skills', []) if cv else [],
#             'status': application.get('status'),
#             'meets_threshold': application.get('meets_threshold'),
#             'qualified_cv': application.get('qualified_cv')
#         })
#     return render_template('hr_view_applied_applicant.html', 
#                          job=job, 
#                          applicants=applicants_data)


from datetime import datetime
import logging
from flask import render_template, flash
import requests

@app.route('/hr_applied_applicant/<int:job_id>')
def hr_view_applied_applicant(job_id):
    # Fetch job details
    job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{job_id}")
    if job_response.status_code != 200:
        flash('Error fetching job details', 'error')
        return render_template('hr_view_applied_applicant.html', jobs=[])
        
    job = job_response.json()
    
    # Fetch applicants for this job
    applicants_response = requests.get(f"{BACKEND_API_URL}/get_applied_job/{job_id}")
    if applicants_response.status_code != 200:
        flash('Error fetching applicants', 'error')
        return render_template('hr_view_applied_applicant.html', job=[])
    
    applicants_data = []
    today = datetime.now().date()
    
    for application in applicants_response.json().get("applications", []):
        # Get applicant details
        logger = logging.getLogger(__name__)
        logger.debug(f"Application: {application}")
        
        # Check for interviews scheduled today or before
        applicant_id = application['applicant_id']
        interviews_response = requests.get(f"{BACKEND_API_URL}/get_interviews/{applicant_id}/{job_id}")
        
        if interviews_response.status_code == 200:
            interviews = interviews_response.json().get('interviews', [])
            has_past_or_current_interview = False
            
            for interview in interviews:
                try:
                    interview_date = datetime.strptime(interview['date'], "%Y-%m-%d").date()
                    if interview_date <= today:
                        has_past_or_current_interview = True
                        break
                except Exception as e:
                    logger.error(f"Error parsing interview date: {e}")
                    continue
            
            if has_past_or_current_interview:
                logger.debug(f"Skipping applicant {applicant_id} - has interview on or before today")
                continue

        # Get user details
        user_response = requests.get(f"{BACKEND_API_URL}/get_user/{applicant_id}")
        if user_response.status_code != 200:
            continue
            
        user = user_response.json()
        user_data = user.get('user', {})
        
        # Get applicant CV
        cv_response = requests.get(f"{BACKEND_API_URL}/get_applicant/{applicant_id}")
        logger.debug(f"CV response: {cv_response.json()}")
        cv_json = cv_response.json()
        cv = cv_json.get('cv_data') if cv_response.status_code == 200 and cv_json.get('status') == 'success' else None

        # Calculate match score
        match_score_str = application.get("passed_criteria", "0/0")
        passed, total = map(int, match_score_str.split("/"))
        passed_criteria_percent = (passed / total) * 100 if total != 0 else 0

        match_score = {
            "passed_criteria_percent": round(passed_criteria_percent, 2),
            "passed_criteria": match_score_str
        }

        applicants_data.append({
            'id': user_data.get('id'),
            'name': f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}",
            'similarity_score': match_score["passed_criteria_percent"],
            'exp_years': cv.get('experience_years', 0) if cv else 0,
            'email': user_data.get('email'),
            'phone_number': user_data.get('phone_number'),
            'skills': cv.get('skills', []) if cv else [],
            'status': application.get('status'),
            'meets_threshold': application.get('meets_threshold'),
            'qualified_cv': application.get('qualified_cv')
        })
    
    return render_template('hr_view_applied_applicant.html', 
                         job=job, 
                         applicants=applicants_data)
# -------- SCHEDULE A MEETING IF MATCH THE BEST SCORE --------
@app.route('/schedule_meeting/<int:applicant_id>/<int:job_id>', methods=['GET', 'POST'])
def schedule_meeting(applicant_id, job_id):
    if 'user_id' not in session:
        flash('Please login', 'error')
        return redirect(url_for('login'))
    
    # Store original IDs before they might get overwritten
    original_applicant_id = applicant_id
    original_job_id = job_id
    
    print(f"Original IDs - Applicant: {original_applicant_id}, Job: {original_job_id}", flush=True)
    
    if request.method == 'POST':
        meeting_id = request.form.get('meeting_id', '')
        meeting_title = request.form['title']
        meeting_date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        
        print(f"Meeting Title: {meeting_title}", flush=True)
    
        # Check if we're updating an existing meeting
        if meeting_id:
            print(f"Updating meeting ID: {meeting_id}", flush=True)
             
            updated_meeting = {
                'meeting_id': meeting_id,
                'meeting_title': meeting_title,
                'meeting_date': meeting_date,
                'start_time': start_time,
                'end_time': end_time,
                'applicant_id': original_applicant_id,  # Use original ID
                'job_id': original_job_id              # Use original ID
            }
            
            if meeting_title == "HR Interview":
                update_response = requests.put(f"{BACKEND_API_URL}/update_interview/{meeting_id}", json=updated_meeting)
            else:
                update_response = requests.put(f"{BACKEND_API_URL}/update_technical_interview/{meeting_id}", json=updated_meeting)
                
            if update_response.status_code == 200:
                print('Meeting updated successfully!', flush=True)
                flash('Meeting updated successfully!', 'success')
            else:
                flash('Failed to update meeting', 'error')
        else:
            if meeting_title == "HR Interview":
                print("HR Interview schedule is being submitted", flush=True)
                user_response = requests.get(f"{BACKEND_API_URL}/get_user/{original_applicant_id}")
                if user_response.status_code != 200:
                    flash('Error fetching user data', 'error')
                    return redirect(url_for('schedule_meeting', applicant_id=original_applicant_id, job_id=original_job_id))
                user_data = user_response.json().get('user', {})

                offered_job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{original_job_id}")
                if offered_job_response.status_code != 200:
                    flash('Error fetching job data', 'error')
                    return redirect(url_for('schedule_meeting', applicant_id=original_applicant_id, job_id=original_job_id))
                offered_job_data = offered_job_response.json().get('job', {})
                
                first_name = user_data.get('first_name', '')
                last_name = user_data.get('last_name', '')
                email = user_data.get('email', '')
                job_title = offered_job_data.get('job_title', '')  
                job_level = offered_job_data.get('job_level', '')  
        
                email_body = f"""
                Dear {first_name} {last_name},

                We are pleased to inform you that you have successfully passed the first stage of our hiring process for the position of **{job_title} ({job_level})** at Hirevo.

                🎉 **Congratulations!**

                We would like to invite you to the next step — an **in-person interview** with our hiring team.

                **Interview Details**
                - **Title:** {meeting_title}
                - **Date:** {meeting_date}
                - **Time:** {start_time} - {end_time}
                - **Location:** Hirevo Offices, American University of Beirut (AUB), Bliss Street, Beirut, Lebanon

                Please make sure to arrive at least 10 minutes early and bring:
                - A copy of your resume
                - A valid ID for entry

                We look forward to meeting you in person!

                Warm regards,  
                **Hirevo HR Team**  
                hr@hirevo.com
                """
                
                job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{original_job_id}")
                if job_response.status_code != 200:
                    flash('Error fetching job details', 'error')
                    return redirect(url_for('jobseeker_dashboard'))
                        
                job_data = job_response.json().get('job', {})
                        
                if job_data.get('status', '').lower() != 'open':
                    flash('This job is no longer available', 'error')
                    return redirect(url_for('jobseeker_dashboard'))
                    
                cv_response = requests.get(f"{BACKEND_API_URL}/get_applicant/{original_applicant_id}")
                cv_data = cv_response.json().get('cv_data', {})
                generate_question_response = requests.post(
                    f"{INTERVIEW_QUESTIONS_URL}/generate-questions",
                    json={
                        'cv': cv_data,
                        'job': job_data
                    }
                )
                
                try:
                    questions_data = generate_question_response.json()
                except ValueError as e:
                    print("Failed to decode questions JSON:", e, flush=True)
                    print("Raw response:", generate_question_response.text, flush=True)
                    flash('Failed to parse questions', 'error')
                    return redirect(url_for('jobseeker_dashboard'))

                msg = Message(
                    subject="You're Invited: Next Step in Your Hirevo Application 🎯",
                    recipients=[email],
                    body=email_body
                )

                save_interview = requests.post(f"{BACKEND_API_URL}/add_interview", json={
                    'interview': {
                        "applicant_id": original_applicant_id,
                        "job_id": original_job_id,
                        'meeting_title': meeting_title,
                        'meeting_date': meeting_date,
                        'start_time': start_time,
                        'end_time': end_time
                    },
                    'questions': questions_data
                })
                
                if save_interview.status_code != 201:
                    print("Add interview failed:", save_interview.status_code, save_interview.text, flush=True)
                    flash('Failed to save interview', 'error')
                    return redirect(url_for('jobseeker_dashboard'))

                mail.send(msg)
                flash('HR Interview scheduled successfully!', 'success')
                
            else:  # Technical Interview
                print("Technical Interview schedule is being submitted", flush=True)
                user_response = requests.get(f"{BACKEND_API_URL}/get_user/{original_applicant_id}")
                if user_response.status_code != 200:
                    flash('Error fetching user data', 'error')
                    return redirect(url_for('schedule_meeting', applicant_id=original_applicant_id, job_id=original_job_id))
                user_data = user_response.json().get('user', {})

                offered_job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{original_job_id}")
                if offered_job_response.status_code != 200:
                    flash('Error fetching job data', 'error')
                    return redirect(url_for('schedule_meeting', applicant_id=original_applicant_id, job_id=original_job_id))
                offered_job_data = offered_job_response.json().get('job', {})
                
                first_name = user_data.get('first_name', '')
                last_name = user_data.get('last_name', '')
                email = user_data.get('email', '')
                job_title = offered_job_data.get('job_title', '')  
                job_level = offered_job_data.get('job_level', '')  
        
                email_body = f"""
                Dear {first_name} {last_name},

                We are pleased to inform you that you have successfully passed the initial stage of our hiring process for the position of **{job_title} ({job_level})** at Hirevo.

                🧠 **Great work so far!**

                We would like to invite you to the next stage — a **technical interview** with our engineering team.

                **Interview Details**
                - **Title:** {meeting_title}
                - **Date:** {meeting_date}
                - **Time:** {start_time} - {end_time}
                - **Location:** Hirevo Offices, American University of Beirut (AUB), Bliss Street, Beirut, Lebanon

                This session will focus on assessing your technical knowledge, problem-solving skills, and familiarity with tools and concepts relevant to the role.

                Please bring:
                - A copy of your updated resume
                - A valid ID for entry
                - A laptop (if applicable or requested)
                - Any supporting materials or portfolios you wish to share

                We're excited to dive deeper into your skills and experience!

                Best regards,  
                **Hirevo HR Team**  
                hr@hirevo.com
                """
                
                msg = Message(
                    subject="You're Invited: Technical Interview at Hirevo 🧠",
                    recipients=[email],
                    body=email_body
                )

                save_interview = requests.post(f"{BACKEND_API_URL}/add_technical_interview", json={
                    'interview': {
                        "applicant_id": original_applicant_id,
                        "job_id": original_job_id,
                        'meeting_title': meeting_title,
                        'meeting_date': meeting_date,
                        'start_time': start_time,
                        'end_time': end_time
                    }
                })

                mail.send(msg)
                flash('Technical Interview scheduled successfully!', 'success')

        return redirect(url_for('schedule_meeting', 
                            applicant_id=original_applicant_id, 
                            job_id=original_job_id))

    # GET request handling
    get_interview_response = requests.get(f"{BACKEND_API_URL}/get_interview")
    stats_response = requests.get(f"{BACKEND_API_URL}/get_dashboard_stats")
    stats = stats_response.json().get('stats', {}) if stats_response.status_code == 200 else {}
    
    if get_interview_response.status_code != 200:
        flash('Error fetching interviews', 'error')
        return render_template('schedule_interview.html', 
                             applicant_id=original_applicant_id, 
                             job_id=original_job_id)

    # GET request handling
    get_interview_response = requests.get(f"{BACKEND_API_URL}/get_interview")
    stats_response = requests.get(f"{BACKEND_API_URL}/get_dashboard_stats")
    stats = stats_response.json().get('stats', {}) if stats_response.status_code == 200 else {}

    if get_interview_response.status_code != 200:
        flash('Error fetching interviews', 'error')
        return render_template('schedule_interview.html', 
                            applicant_id=original_applicant_id, 
                            job_id=original_job_id)

    interviews = get_interview_response.json().get('interviews', [])
    meeting_data = []

    for interview in interviews:
        # Get user data directly from the API
        user_response = requests.get(f"{BACKEND_API_URL}/get_user/{interview['applicant_id']}")
        if user_response.status_code != 200:
            continue
        
        user_data = user_response.json().get('user', {})
        full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}"
        
        # Get job data directly from the API
        job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{interview['job_id']}")
        if job_response.status_code != 200:
            continue
        
        job_data = job_response.json().get('job', {})
        job_title = job_data.get('title', 'Unknown Job')
        
        meeting_data.append({
            "applicant_name": full_name,
            "job_title": job_title,
            "meeting_title": interview.get('meeting_title', 'Untitled'),
            "meeting_date": interview.get('meeting_date', ''),
            "start_time": interview.get('start_time', ''),
            "end_time": interview.get('end_time', ''),
            "interview_id": interview.get('id', '')  # Include interview ID for updates
        })

    return render_template('schedule_interview.html', 
                         meetings=meeting_data, 
                         applicant_id=original_applicant_id,
                         job_id=original_job_id)
# -------- DISPLAY ALL JOB OFFERED  --------
### Offered Job List ###
@app.route('/offered_job')
def offered_job():
    if 'user_id' not in session:
        flash('Please login', 'error')
        return redirect(url_for('login'))
    
    try:
        # Get jobs posted by department
        hr_id = session['user_id']
        job_offere_response = requests.get(f"{BACKEND_API_URL}/get_offered_job")
        stats_response = requests.get(f"{BACKEND_API_URL}/get_dashboard_stats")
        stats = stats_response.json().get('stats', {}) if stats_response.status_code == 200 else {}
        if job_offere_response.status_code != 200:
            flash('Error fetching your department jobs', 'error')
            return render_template('offered_job.html', jobs=[])
        
        jobs = job_offere_response.json().get('jobs', [])

        job_ids = [job['id'] for job in jobs]

      # get name of the department based on department id
        for job in jobs:
            dept_id = job['dept_id']
            dept_response = requests.get(f"{BACKEND_API_URL}/get_department/{dept_id}")
            dept_response.raise_for_status()
            department = dept_response.json().get('department', [])
            job['department_name'] = department['department_name']
        return render_template('offered_job.html', jobs=jobs, stats=stats)
    
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('offered_job.html', jobs=[], stats={})
    
# @app.route('/offered_job')
# def offered_job():
#     if 'user_id' not in session:
#         flash('Please login', 'error')
#         return redirect(url_for('login'))
    
#     try:
#         job_offer_response = requests.get(f"{BACKEND_API_URL}/get_offered_job")
        
#         if job_offer_response.status_code != 200:
#             flash('Error fetching jobs', 'error')
#             return render_template('offered_job.html', jobs=[])
        
#         jobs = job_offer_response.json().get('jobs', [])
#         return render_template('offered_job.html', jobs=jobs)
    
#     except Exception as e:
#         flash(f'Error loading jobs: {str(e)}', 'error')
#         return render_template('offered_job.html', jobs=[])
# -------- DISPLAY QUESTION FOR INTERVIEW AND FILTER BY DAY --------
@app.route('/weekly_questions')
def weekly_questions():    
    try:
        selected_date = request.args.get('date', None)
        if not selected_date:
            today = datetime.now()
            selected_date = today.strftime('%Y-%m-%d')

        date_obj = datetime.strptime(selected_date, '%Y-%m-%d')

        # Fetch interviews
        get_interview_response = requests.get(f"{BACKEND_API_URL}/get_interview")
        if get_interview_response.status_code != 200:
            flash('Error fetching interviews', 'error')
            return redirect(url_for('company_dashboard'))

        interviews = get_interview_response.json().get('interviews', [])

        # Fetch answered interviews
        answers_response = requests.get(f"{BACKEND_API_URL}/get_interview_answers")
        answered_ids = set()
        if answers_response.status_code == 200:
            answers = answers_response.json().get('answers', [])
            answered_ids = {answer['interview_id'] for answer in answers}

        questions = []

        for interview in interviews:
            applicant_id = interview.get('applicant_id')
            job_id = interview.get('job_id')
            interview_id = interview.get('id')
            raw_date = interview.get('meeting_date', '')

            try:
                interview_date = datetime.strptime(raw_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                interview_date = raw_date

            if interview_date != selected_date:
                continue

            # Get user info
            user_response = requests.get(f"{BACKEND_API_URL}/get_user/{applicant_id}")
            if user_response.status_code != 200:
                continue
            user_data = user_response.json()
            user_info = user_data.get('user', {})
            full_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}"
            # Get job info
            job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{job_id}")
            if job_response.status_code != 200:
                continue
            job_data = job_response.json()
            job_info = job_data.get('job', {})
            job_title = job_info.get('title')
            # Format time
            time_range = f"{interview.get('start_time', '')} - {interview.get('end_time', '')}"

            # Parse questions
            print("interviews", interview)
            raw_questions = interview.get('questions')
            if isinstance(raw_questions, dict) and 'questions' in raw_questions:
                raw_questions = raw_questions['questions']

            questions_by_category = {
                category_name.capitalize(): q_list if isinstance(q_list, list) else [q_list]
                for category_name, q_list in raw_questions.items()
}

            date_obj = datetime.strptime(interview_date, '%Y-%m-%d')
            questions.append({
                "id": interview_id,
                "applicant_name": full_name,
                "job_title": job_title,
                "questions": raw_questions,
                "interview_date": interview_date,
                "interview_time": time_range,
                "status": interview_id in answered_ids,
                "day_of_week": date_obj.strftime('%A')
            })

        # Calculate progress
        total_questions = len(questions)
        answered_questions = len([q for q in questions if q['status']])
        progress_percent = (answered_questions / total_questions * 100) if total_questions > 0 else 0

        # Format selected date
        selected_date_display = date_obj.strftime('%A, %b %d, %Y')
        day_of_week = date_obj.strftime('%A')

        return render_template('weekly_questions.html', 
                               questions=questions,
                               progress_percent=progress_percent,
                               total_questions=total_questions,
                               answered_questions=answered_questions,
                               selected_date=selected_date,
                               selected_date_display=selected_date_display,
                               day_of_week=day_of_week)

    except Exception as e:
        flash(f'Error loading questions: {str(e)}', 'error')
        today = datetime.now()
        return render_template('weekly_questions.html', 
                               questions=[], 
                               selected_date=today.strftime('%Y-%m-%d'),
                               selected_date_display=today.strftime('%A, %b %d, %Y'),
                               day_of_week=today.strftime('%A'))


# -------- DISPLAY INTERVIEW QUESTIONS AND THEIR ANSWERS  --------
@app.route('/answer_question/<int:question_id>')
def answer_question(question_id):
    print("submit", question_id, flush=True)
    """Display a form with a list of questions to answer."""
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
  
    try:
        # Fetch interview data from the backend
        get_interview_response = requests.get(f"{BACKEND_API_URL}/get_interview/{question_id}")
        print("Response content:", get_interview_response.json(), flush=True)
        
        # Check if the response is successful
        if get_interview_response.status_code != 200:
            flash('Error fetching interviews', 'error')
            return redirect(url_for('company_dashboard'))

        # Extract questions from the response
        response_data = get_interview_response.json()
        questions_by_category = response_data.get('interview', {}).get('questions', {}).get('questions', {})
        if not questions_by_category:
            print("No questions found in the response", flush=True)
            flash('No questions found for this interview', 'error')
            return redirect(url_for('weekly_questions'))
        
        # Flatten the questions into a single list
        flattened_questions = []
        for category, question_list in questions_by_category.items():
            for question in question_list:
                flattened_questions.append(question)

        # Render the template with the flattened questions
        return render_template('answer_question.html', questions=flattened_questions, target_question_id=question_id)
    
    except Exception as e:
        print("Error:", str(e), flush=True)
        flash(f'Error loading questions: {str(e)}', 'error')
        return redirect(url_for('weekly_questions'))

# -------- SUBMIT ANSWERS OF INTERVIEW QUESTION  --------
@app.route('/submit_answers/<int:interview_id>', methods=['POST'])
def submit_answers(interview_id):
    """Process the submitted answers for multiple questions."""
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    try:
        # Get all the answers from the form
        answers = []
        for key, value in request.form.items():
            if key.startswith('answer_'):
                question_id = int(key.split('_')[1])
                answers.append((question_id, value))

        print("answers", answers, flush=True)
       
     
        # Save the answer to the database
        save_response = requests.post(f"{BACKEND_API_URL}/add_interview_answers", json={
                'interview_id': interview_id,
                'answers': answers
            })
            
        if save_response.status_code != 201:
            flash(f'Error saving answer for question {question_id}', 'error')
         
        print("int", interview_id)        
        # get interview table 
        interview_response = requests.get(f"{BACKEND_API_URL}/get_interview/{interview_id}")    
        if interview_response.status_code != 200:
                flash(f'Error getting question', 'error')
                return redirect(url_for('weekly_questions'))
        interview_data = interview_response.json().get('interview', {})
        job_id = interview_data.get('job_id')
        applicant_id = interview_data.get('applicant_id')
        questions = interview_data.get('questions', {}).get('questions', {})

        print("Job ID:", job_id, flush=True)
        print("Applicant ID:", applicant_id, flush=True)
        print("Questions:", questions, flush=True)

        applied_job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{job_id}")    
        if applied_job_response.status_code != 200:
            flash(f'Error getting job', 'error')
            return redirect(url_for('weekly_questions'))
        print("applied_job_response", applied_job_response.json(), flush=True)
        applied_data = applied_job_response.json().get('job', {})
        requirements = applied_data.get("requirements")
        responsibilities = applied_data.get("responsibilities")

        # Evaluate the answer using the Evaluation_Question model
        answers_dict = {q_id: ans for q_id, ans in answers}
        print("answers_dict", answers_dict, flush=True)
        # Now call the evaluation API
        eval_response = requests.post(f"{ANSWER_EVALUATION_URL}/evaluate", json={
            'interview_questions': questions, 
            'interview_answers': answers_dict,
            'requirements': requirements,
            'responsibilities': responsibilities
        })
        print("eval_response", eval_response.json(), flush=True)    
        if eval_response.status_code != 200:
                flash(f'Answer saved but evaluation failed for question ', 'warning')
                return redirect(url_for('weekly_questions'))
               
        evaluation = eval_response.json().get('evaluation', {})
        overall_scores = evaluation.get('overall_scores', {})
        print("Overall Scores:", overall_scores, flush=True)
        requirements_scores = overall_scores.get("requirements", {})
        responsibilities_scores = overall_scores.get("responsibilities", {})

        # Extract the scores, defaulting to 0.0 if not present
        req_avg = requirements_scores.get("average_score_all_answers", 0.0)
        resp_avg = responsibilities_scores.get("average_score_all_answers", 0.0)

        # Calculate the average of the two
        final_average = (req_avg + resp_avg) / 2
            
        if save_response.status_code != 201:
                flash(f'Error saving evaluation', 'error')
            
                
  
        user_response = requests.get(f"{BACKEND_API_URL}/get_user/{applicant_id}")
        if user_response.status_code != 200:
                flash('Error fetching user data', 'error')
                return redirect(url_for('weekly_questions'))
              
        user_data = user_response.json().get('user', {})

        offered_job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{job_id}")
        if  offered_job_response.status_code != 200:
                flash('Error fetching job data', 'error')
                return redirect(url_for('weekly_questions'))
               
        offered_job_response = user_response.json().get('', {})

            
            # Assume you've extracted this data:
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        email = user_data.get('email', '')
        job_title =  offered_job_response.get('job_title', '')  
        job_level = offered_job_response.get('job_level', '')  

        # Get all answers
        if final_average >= 0.2:
            email_body = f"""
            Dear {first_name} {last_name},

            We are pleased to inform you that you have successfully passed the second stage of our hiring process for the position of **{job_title} ({job_level})** at Hirevo.  

            🎉 **Congratulations!**  

            You are now advancing to the **technical interview**, which will be scheduled shortly. We will send you the details (date, time, and format) very soon.  

            In the meantime, please ensure you are prepared for a technical discussion relevant to the role. If you have any questions or need assistance, feel free to reply to this email.  

            We appreciate your patience and look forward to continuing the process with you!  

            Warm regards,  
            **Hirevo HR Team**  
            hr@hirevo.com  
            """
            msg = Message(
                subject="Passed the Second Phase – Technical Interview Coming Soon 🎯",
                recipients=[email],
                body=email_body
            )

            mail.send(msg)

            # Update the status in the backend
            update_status_response = requests.put(f"{BACKEND_API_URL}/update_application_status", json={
                "applicant_id": applicant_id,
                "job_id": job_id,
                "status": "technical_interview"
            })

            if update_status_response.status_code == 200:
                print("Status updated successfully", flush=True)
            else:
                print(f"Failed to update status: {update_status_response.status_code}", flush=True)
        else:
            # Send rejection email
            email_body = f"""
            Dear {first_name} {last_name},

            Thank you for taking the time to apply for the **{job_title} ({job_level})** position at Hirevo.  

            After careful consideration, we regret to inform you that we have decided to move forward with other candidates whose qualifications more closely match our current needs.  

            We genuinely appreciate your interest in Hirevo and encourage you to apply for future opportunities.  

            Wishing you the best in your job search and future career endeavors.  

            Warm regards,  
            **Hirevo HR Team**  
            hr@hirevo.com  
            """
            msg = Message(
                subject="Application Update – Thank You for Applying",
                recipients=[email],
                body=email_body
            )

            mail.send(msg)

            # Update the status in the backend
            update_status_response = requests.put(f"{BACKEND_API_URL}/update_application_status", json={
                "applicant_id": applicant_id,
                "job_id": job_id,
                "status": "rejected"
            })

            if update_status_response.status_code == 200:
                print("Status updated to rejected successfully", flush=True)
            else:
                print(f"Failed to update status to rejected: {update_status_response.status_code}", flush=True)
        # Fetch the interview answers
        get_interview = requests.get(f"{BACKEND_API_URL}/get_interview_answers/{interview_id}")
        if get_interview.status_code == 200:
            print("id", get_interview.json(), flush=True)
            answer_id = get_interview.json().get('answers', {}).get('id')
            if answer_id:
                # Save the answer evaluation to the database
                if final_average >= 0.2:
                    save_response = requests.post(f"{BACKEND_API_URL}/add_answer_evaluation", json={
                        "answer_id": answer_id,
                        "avg_score_requirements": req_avg,
                        "avg_score_responsibilities": resp_avg,
                        'full_evaluation': evaluation,
                        "qualified_interview": True
                    })
                else:
                    save_response = requests.post(f"{BACKEND_API_URL}/add_answer_evaluation", json={
                        "answer_id": answer_id,
                        "avg_score_requirements": req_avg,
                        "avg_score_responsibilities": resp_avg,
                        'full_evaluation': evaluation,
                        "qualified_interview": False
                    })
            else:
                flash('Answer ID not found in the response', 'error')
        else:
            flash('Error fetching interview answers', 'error')
#             offered_job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job") 

#             if offered_job_response.status_code != 201:
#                 flash(f'Error getting job', 'error')  
#                 return redirect(url_for('weekly_questions'))

#             jobs = offered_job_response.json().get('jobs') 
#             eval_all_response = requests.post(f"{JOB_MATCHER_ALL_URL}/evaluate-multi-job", json={
#                'interview_questions': questions, 
#                'interview_answers': answers,
#                 'jobs': jobs,
               
#             })
#             best_match = eval_all_response.json().get('best_match')
#             best_match = eval_all_response.json().get('best_match', {})

#             # Extract overall scores
#             overall_scores = best_match.get('overall_scores', {})
#             requirements_scores = overall_scores.get("requirements", {})
#             responsibilities_scores = overall_scores.get("responsibilities", {})

#             # Extract average_score_all_answers with default values
#             req_avg = requirements_scores.get("average_score_all_answers", 0.0)
#             resp_avg = responsibilities_scores.get("average_score_all_answers", 0.0)

#             # Calculate combined average
#             final_average = (req_avg + resp_avg) / 2

          
#             if final_average < 50:
#                 email_body = f"""
#                 Dear {first_name} {last_name},

#                 Thank you for your interest in the **{job_title} ({job_level})** position at Hirevo.

#                 After careful consideration, we regret to inform you that at this time, we will not be moving forward with your application for this or any current openings.  

#                 Please know that this decision was not easy, and it does not reflect negatively on your qualifications or experience. We encourage you to apply again in the future as new opportunities arise.  

#                 We sincerely appreciate the time and effort you invested in the application process.  

#                 Wishing you the best in your job search and future endeavors.  

#                 Warm regards,  
#                 **Hirevo HR Team**  
#                 hr@hirevo.com  
#                 """

#                 msg = Message(
#                     subject="Application Update from Hirevo",
#                     recipients=[email],
#                     body=email_body
#                 )

#                 mail.send(msg)
#             else:
#                 cv_response = requests.get(f"{BACKEND_API_URL}/get_applicant/{applicant_id}")
#                 cv_data = cv_response.json().get('cv_data', {})

#                 # final descision
#                 FINAL_DECISION_URL_response = requests.post(f"{FINAL_DECISION_URL}/final-decision", json={
#                'cv_data': cv_data, 
#                 'jobs': jobs,
               
#                  }) 
#                 evaluation = FINAL_DECISION_URL_response.json().get('evaluation', {})

#                 # Extract and clean percentage_met
#                 percentage_str = evaluation.get('percentage_met', '0%')
#                 percentage_number = float(percentage_str.strip('%'))

#                 # Extract final_reason
#                 final_reason = evaluation.get('final_reason', 'No reason provided')
                
#                 job_title_best = eval_all_response.json().get('job_title')
#                 job_level_best = eval_all_response.json().get('job_level')
#                 evaluation =  eval_all_response.json().get('job_level')
#                 if percentage_number >= 50:
#                     email_body = f"""
#                     Dear {first_name} {last_name},

#                     Thank you for taking part in our hiring process.

#                     While you were not selected for the position of **{job_title} ({job_level})**, we’re excited to let you know that you've been identified as a strong candidate for another opportunity at Hirevo:  
#                     **{job_title_best} ({job_level_best})**.


#                     We believe this role better aligns with your background and skills, and we’re pleased to proceed with your application under this new track.

#                     If you have any questions in the meantime, feel free to reach out.

#                     We’re looking forward to moving ahead with you!

#                     Warm regards,  
#                     **Hirevo HR Team**  
#                     hr@hirevo.com  
#                     """

#                     msg = Message(
#                         subject="New Opportunity Match at Hirevo 🎯",
#                         recipients=[email],
#                         body=email_body
#                     )

#                     mail.send(msg)
#                     # Save the answer to the database

#                     save_response = requests.post(f"{BACKEND_API_URL}/add_best_match", json={
#                         "applicant_id": applicant_id,
#                         'job_id': job_id,
#                         "evaluation": evaluation

#                     })
#                 else:
#                     email_body = """"
#                     Dear {first_name} {last_name},

#                     Thank you for taking the time to interview with us for the {job_title} position at Hirevo. We appreciate the effort you put into the process and the opportunity to learn more about your skills and experience.

#                     After careful consideration, we regret to inform you that your profile does not currently meet the specific requirements for this role or other open positions at Hirevo. {final_reason}

#                     While we don’t have a match for you at this time, we encourage you to stay connected with us for future opportunities that may align better with your background.

#                     We sincerely appreciate your interest in joining our team and wish you the best in your job search.

#                     Warm regards,
#                     Hirevo HR Team
#                     hr@hirevo.com
#                     """

        flash('Your answers have been submitted successfully', 'success')
        return redirect(url_for('weekly_questions'))
    
    except Exception as e:
        flash(f'Error processing answers: {str(e)}', 'error')
        return redirect(url_for('weekly_questions'))

# # -------- VIEW INTERVIEW ANSWERS AND THEIR QUESTIONS  --------
@app.route('/view_answer/<int:question_id>')
def view_answer(question_id):
    """View a previously submitted answer."""
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    try:
        # Fetch the interview questions from the backend
        interview_response = requests.get(f"{BACKEND_API_URL}/get_interview/{question_id}")
        if interview_response.status_code != 200:
            flash('Error fetching interview data', 'error')
            return redirect(url_for('weekly_questions'))
        
        interview_data = interview_response.json().get('interview', {})
        questions_by_category = interview_data.get('questions', {}).get('questions', {})

        # Flatten the questions into a single list
        questions = []
        for category, question_list in questions_by_category.items():
            questions.extend(question_list)

        print("Flattened questions:", questions, flush=True)

        # Fetch the answers for the interview
        answers_response = requests.get(f"{BACKEND_API_URL}/get_interview_answers/{question_id}")
        print("ans", answers_response, flush=True)
        if answers_response.status_code != 200:
            flash('Error fetching answers', 'error')
            return redirect(url_for('weekly_questions'))
        
        answers_data = answers_response.json().get('answers', {}).get('answers', [])

        # Align answers with questions
        aligned_answers = []
        for i, question in enumerate(questions):
            # Find the corresponding answer for the question
            answer_text = next((answer[1] for answer in answers_data if answer[0] == i + 1), "No answer provided")
            aligned_answers.append({
                "question": question,
                "answer": answer_text
            })

        # Fetch the evaluation score
        evaluation_response = requests.get(f"{BACKEND_API_URL}/get_answer_evaluation/{question_id}")
        evaluation = evaluation_response.json().get('evaluation', {}).get('avg_score_requirements', 0)

        # Prepare the data for rendering
        data = {
            'questions_and_answers': aligned_answers,
            'evaluation': evaluation
        }
        
        return render_template('view_answer.html', answer=data)
    
    except Exception as e:
        print(e)
        flash(f'Error loading answer: {str(e)}', 'error')
        return redirect(url_for('weekly_questions'))

import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
# -------- LIST OF APPLICANT APPLIED TO A JOB--------
@app.route('/hr_view_technical_interview_applicant/<int:job_id>')
def hr_view_technical_interview_applicant(job_id):
    try:
        logger.debug(f"Fetching job details for job_id: {job_id}")
        job_response = requests.get(f"{BACKEND_API_URL}/get_offered_job/{job_id}")
        logger.debug(f"Job Response: {job_response.json()}")

        if job_response.status_code != 200:
            flash('Error fetching job details', 'error')
            return render_template('hr_view_applied_applicant.html', job={}, applicants=[])

        job_data = job_response.json().get('job', {})
        job = {
            "job": {
                "id": job_data.get('id'),
                "job_title": job_data.get('title'),  # Corrected key
                "job_level": job_data.get('job_level'),
                "years_experience": job_data.get('years_experience'),
                "date_offering": job_data.get('date_offered'),  # Corrected key
                "status": job_data.get('status')
            }
        }
        logger.debug(f"Parsed Job Data: {job}")

        # Fetch applicants for this job
        applied_response = requests.get(f"{BACKEND_API_URL}/get_applied_job/{job_id}")
        logger.debug(f"Applied Response: {applied_response.json()}")

        if applied_response.status_code != 200:
            flash('Error fetching applicants', 'error')
            return render_template('hr_view_applied_applicant.html', job=job, applicants=[])

        applicants_data = []
        for application in applied_response.json().get('applications', []):
            logger.debug(f"Processing application: {application}")
            # Process each application...

        return render_template('hr_view_applied_applicant.html', job=job, applicants=applicants_data)

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return render_template('hr_view_applied_applicant.html', job={}, applicants=[])
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
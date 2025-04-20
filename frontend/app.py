from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import requests
import os
from datetime import datetime
from flask_mail import Mail, Message



app = Flask(__name__)

# Configuring Flask-Mail with Gmail and your App Password
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'zynab.ahmad.saad@gmail.com'  # Replace with your Gmail
app.config['MAIL_PASSWORD'] = 'teyv eues tgoq ipvt'    # ← Your App Password


mail = Mail(app)
# To be Changes 
app.secret_key = 'dev-key-123-abc!@#'

DATABASE_URL = os.getenv('DATABASE_URL', 'http://database:5002')
CV_JOB_MATCHER_URL = os.getenv('CV_JOB_MATCHER_URL', 'http://cv-job-matcher:5003')
JOB_GENERATOR_URL = os.getenv('JOB_GENERATOR_URL', 'http://job-generator:5004')
Interview_Questions_URL = os.getenv('Interview_Questions_URL', 'http://cv-job-matcher:5005')


# Main Dashboard
@app.route('/')
def index():
    return render_template('index.html')

### Login ###
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        register_option = request.form.get('user_type')
        
        if not email or not password or not register_option:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('login'))
        
        try:
            # verify credentials for login user
            auth_response = requests.post(f"{DATABASE_URL}/login", json={
                    'email': email,
                    'password': password,
                    'register_option': register_option
                })
                
            if auth_response.status_code == 200:
                    data = auth_response.json()
                    session['user_id'] = data.get('user_id')
                    session['register_option'] = data.get('register_option')
                    session['email'] = email
                    
                    # Redirect based on user type
                    if data.get('register_option') == 'company':
                        if session['user_id'] == 1:
                            return redirect(url_for('hr_dashboard'))
                        else:
                            return redirect(url_for('company_dashboard'))
                    
                    return redirect(url_for('jobseeker_dashboard'))
            else:
                flash('Invalid email or password', 'error')
                    
        except requests.exceptions.RequestException as e:
            flash('Connection error: Please try again later', 'error')
        except Exception as e:
            flash('An unexpected error occurred', 'error')
            print(f"Login error: {str(e)}")
        
        return redirect(url_for('login')) 
    return render_template('login.html')

### Signup ###
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone_number')
        date = request.form.get('dob')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # confirm that password and confirm one are matched 
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))
        
        # check that entry are not missing 
        if not all([first_name, last_name, email, phone, date, password, confirm_password]):
            flash('All fields are required', 'error')
            return redirect(url_for('signup'))
        
        try:
            # Call database service to create user
            response = requests.post(f"{DATABASE_URL}/signup", json={
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'date':date,
                'phone_number': phone,
                'password': password
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

### jobseeker required view function ###

### Upload CV ###
# Configuration of allowed file
ALLOWED_EXTENSIONS = {'pdf'} # alowed extension
MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB limit

# function to the allowed file
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_cv', methods=['GET', 'POST'])
def upload_cv():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
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
                # Extract content of cv file 
                files = {'file': (file.filename, file.stream, file.mimetype)}
                response = requests.post(
                    "http://cv-extraction:5001/extract-cv",
                    files=files
                )
                
                if response.status_code == 200:
                    cv_data = response.json().get('cv_data', {})
                    
                  
                    # save csv info using user id
                    save_response = requests.post(
                        f"{DATABASE_URL}/add_applicant",
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

### jobseeker profile ###
@app.route('/profile')
def jobseeker_profile():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    try:
        # Get user info from database API
        user_response = requests.get(f"{DATABASE_URL}/get_user/{session['user_id']}")
        if user_response.status_code != 200:
            flash('Error fetching user data', 'error')
            return redirect(url_for('jobseeker_dashboard'))
        
        user_data = user_response.json().get('user', {})
        
        # Get application info if exists
        application_response = requests.get(
            f"{DATABASE_URL}/get_applicat/{session['user_id']}"
        )
        if application_response.status_code != 200:
            flash('Error fetching application data', 'error')
            return redirect(url_for('jobseeker_dashboard'))
        
        application_data = user_response.json().get('cv_data', {})
 
        return render_template('profile.html', 
                            user=user_data, 
                            application=application_data)
    
    except Exception as e:
        flash(f'Error loading profile: {str(e)}', 'error')
        return redirect(url_for('jobseeker_dashboard'))


### Jobseeker dashboard ###
@app.route('/jobseeker_dashboard', methods=['GET', 'POST'])
def jobseeker_dashboard():
    # if 'user_id' not in session:
    #     flash('Please login first', 'error')
    #     return redirect(url_for('login'))
    
    try:
        # Get all jobs from database
        response = requests.get(f"{DATABASE_URL}/get_offered_job")
        if response.status_code != 200:
            flash('Error fetching jobs', 'error')
            return render_template('jobseeker_dashboard.html', jobs=[])
        
        jobs = response.json().get('jobs', [])

        # Filter only open jobs
        open_jobs = [job for job in jobs if job.get('status', '').lower() == 'open']

        # get name of the department based on department id
        for job in open_jobs:
            dept_id = job['dept_id']
            dept_response = requests.get(f"{DATABASE_URL}/get_department/{dept_id}")
            dept_response.raise_for_status()
            department = dept_response.json().get('department', [])
            job['department_name'] = department['department_name']
        
        # Check if user has uploaded CV
        cv_response = requests.get(f"{DATABASE_URL}/get_applicant/{session['user_id']}")
        has_cv = cv_response.status_code == 200 and cv_response.json().get('cv_data') is not None

        # If user apply for a Job 
        if request.method == 'POST':
            job_id = request.form.get('job_id')

            # check if user upload his cv
            if not has_cv:
                flash('Please upload your CV before applying for jobs', 'error')
                return redirect(url_for('jobseeker_dashboard'))


            if job_id:
                # Get a Job 
                job_response = requests.get(f"{DATABASE_URL}/get_offered_job/{job_id}")
                if job_response.status_code != 200:
                    flash('Error fetching job details', 'error')
                    return redirect(url_for('jobseeker_dashboard'))
                
                job_data = job_response.json().get('job', {})
                
                # check if the status of job is open
                if job_data.get('status', '').lower() != 'open':
                    flash('This job is no longer available', 'error')
                    return redirect(url_for('jobseeker_dashboard'))
                # Get CV data
                cv_data = cv_response.json().get('cv_data', {})

                # Match CV with job
                match_response = requests.post(
                    f"{CV_JOB_MATCHER_URL}/cv-job-match",
                    json={
                        'cv': cv_data,
                        'job': job_data
                    }
                )

                if match_response.status_code == 200:
                    match_result = match_response.json().get('result', {})
                
                # Save application
                application_response = requests.post(
                    f"{DATABASE_URL}/add_applied_job",
                    json={
                        'applicant_id': session['user_id'],
                        'job_id': job_id,
                        'status': 'scheduling_interview',
                        "result": match_result
                    }
                )
                
                if application_response.status_code == 201:
                    flash('Application submitted successfully!', 'success')
                else:
                    flash('Error submitting application', 'error')
                
                return redirect(url_for('jobseeker_dashboard'))
        
        return render_template('jobseeker_dashboard.html', jobs=open_jobs)
    
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('jobseeker_dashboard.html', jobs=[])

### company required view functions ###

### company dashboard ###
@app.route('/company_dashboard')
def company_dashboard():
    # if 'user_id' not in session:
    #     flash('Please login', 'error')
    #     return redirect(url_for('login'))
    
    try:
        # Get jobs posted by department
        dept_id = session['user_id']
        job_offere_response = requests.get(f"{DATABASE_URL}/get_offered_job/{dept_id}")
        
        if job_offere_response.status_code != 200:
            flash('Error fetching your department jobs', 'error')
            return render_template('company_dashboard.html', jobs=[])
        
        jobs = job_offere_response.json().get('jobs', [])

        job_ids = [job['ID'] for job in jobs]

        # 2. Get all applicants who applied to these jobs
        applicants = []
        if job_ids:
            applicants_response = requests.post(f"{DATABASE_URL}/get_all_applicants/{job_ids}")
            
            if applicants_response.status_code == 200:
                applicants = applicants_response.json().get('applicants', [])

        # 3. Prepare statistics
        stats = {
            'total_jobs': len(jobs),
            'open_jobs': sum(1 for job in jobs if job['status'] == 'open'),
            'closed_jobs': sum(1 for job in jobs if job['status'] == 'closed'),
            'total_applicants': len(applicants),         
        }

        return render_template(
            'department_dashboard.html',
            jobs=jobs,
            stats=stats
        )

    except Exception as e:
       flash(f'Error loading dashboard: {str(e)}', 'error')
    jobs=  [
        {
        "id": 42,
        "title": "Senior Python Developer",
        "description": "We're looking for an experienced Python developer...",
        "company_id": 15,
        "job_level": "Senior",
        "years_experience": "5+ years",
        "responsibilities": ["Design services", "Mentor juniors"],
        "requirements": ["5+ Python", "Flask/Django"],
        "created_at": "2023-11-15T14:30:22.123456",
        "company": {
            "id": 15,
            "name": "Tech Innovations Inc."
        },
        "applicant_count": 8
        },
        {
        "id": 43,
        "title": "Frontend Engineer",
        "description": "Looking for React specialist...",
        "company_id": 15,
        "job_level": "Mid Level",
        "years_experience": "3-5 years",
        "responsibilities": ["Build UIs", "Optimize performance"],
        "requirements": ["3+ React", "TypeScript"],
        "created_at": "2023-11-10T09:15:33.456789",
        "company": {
            "id": 15,
            "name": "Tech Innovations Inc."
        },
        "applicant_count": 12
        },
         {
        "id": 43,
        "title": "Frontend Engineer",
        "description": "Looking for React specialist...",
        "company_id": 15,
        "job_level": "Mid Level",
        "years_experience": "3-5 years",
        "responsibilities": ["Build UIs", "Optimize performance"],
        "requirements": ["3+ React", "TypeScript"],
        "created_at": "2023-11-10T09:15:33.456789",
        "company": {
            "id": 15,
            "name": "Tech Innovations Inc."
        },
        "applicant_count": 12
        },
         {
        "id": 43,
        "title": "Frontend Engineer",
        "description": "Looking for React specialist...",
        "company_id": 15,
        "job_level": "Mid Level",
        "years_experience": "3-5 years",
        "responsibilities": ["Build UIs", "Optimize performance"],
        "requirements": ["3+ React", "TypeScript"],
        "created_at": "2023-11-10T09:15:33.456789",
        "company": {
            "id": 15,
            "name": "Tech Innovations Inc."
        },
        "applicant_count": 12
        }
    ]
    stats = {
            'total_jobs': 2,
            'open_jobs': 2,
            'closed_jobs': 2,
            'total_applicants': 2,     
        }
    
        # return render_template('company_dashboard.html', jobs=[])
    return render_template('company_dashboard.html',jobs=jobs, stats=stats)

### view all offered Job ###
@app.route('/view_all_jobs')
def view_all_jobs():
    try:
        dept_id = session['user_id']
        job_offere_response = requests.get(f"{DATABASE_URL}/get_offered_job/{dept_id}")
        
        if job_offere_response.status_code != 200:
            flash('Error fetching jobs', 'error')
            return redirect(url_for('company_dashboard'))
        
        jobs = job_offere_response.json().get('jobs', [])
        
        return render_template('all_jobs.html', jobs=jobs)
        
    except Exception as e:
        flash(f'Error loading jobs: {str(e)}', 'error')
        return redirect(url_for('company_dashboard'))
    
@app.template_filter('format_date')
def format_date_filter(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
        return date_obj.strftime('%b %d, %Y')
    except:
        return date_str
    
@app.route('/post_job', methods=['POST','GET'])
def post_job():
    # if 'user_id' not in session:
    #     flash('Please login first', 'error')
    #     return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Validate required fields first
            required_fields = ['jobTitle', 'jobLevel', 'yearsExperience']
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

        match_response = requests.post(
                    f"{CV_JOB_MATCHER_URL}/cv-job-match",
                    json={
                    'job_title' : job_data['job_title'],
                    'department_id' : job_data['department_id'],
                    'job_level' : job_data['job_level'],
                    'years_experience' : job_data['years_experience'],
                    'additional_info' : job_data['additional_info']   
                    }
                ) 
        if match_response.status_code != 200:
                    flash('Error Extract job description', 'error')
                    return redirect(url_for('post_job'))
 
        job_description = match_response.json().get('job_description', {})

        add_offer_job_response = requests.post(f"{DATABASE_URL}/add_offer_job", json={
                    'job_title' : job_data['job_title'],
                    'department_id' : job_data['department_id'],
                    'job_level' : job_data['job_level'],
                    'years_experience' : job_data['years_experience'],
                    'additional_info' : job_data['additional_info'],
                    'date_offering': datetime.now(),
                    'status': "open",
                    "job_description": job_description
                })
        if add_offer_job_response.status_code != 200:
                    flash('Error In Saving job Offere', 'error')
                    return redirect(url_for('post_job'))
        
    return render_template('post_job.html')



@app.route('/job_applicants/<int:job_id>')
def job_applicants(job_id):
    # try:
    #     # First get the job details
    #     job_response = requests.get(f"{DATABASE_URL}/jobs/{job_id}")
    #     if job_response.status_code != 200:
    #         flash('Job not found', 'error')
    #         return redirect(url_for('company_dashboard'))
            
    #     job = job_response.json().get('job')
        
    #     # Verify this company owns the job
    #     if job['company']['id'] != session.get('user_id'):
    #         flash('You can only view applicants for your own jobs', 'error')
    #         return redirect(url_for('company_dashboard'))
        
    #     # Get all applications from the database
    #     applications_response = requests.get(f"{DATABASE_URL}/get_applications")
    #     if applications_response.status_code != 200:
    #         flash('Error fetching applications', 'error')
    #         return render_template('job_applicants.html', job=job, applicants=[])
            
    #     all_applications = applications_response.json().get('applications', [])
        
    #     # For demo purposes, we'll just return all applications
    #     # In a real app, you'd want to filter applications that actually applied to this job
    #     # You would need an "applications" table that links users to jobs they applied for
        
    #     return render_template('job_applicants.html', 
    #                          job=job, 
    #                          applicants=all_applications)
    
    # except Exception as e:
    #     flash(f'Error: {str(e)}', 'error')
    #     return redirect(url_for('company_dashboard'))
    
    # test
    job= [
    {
        "id": 42,
        "title": "Senior Python Developer",
        "description": "We're looking for an experienced Python developer to join our team...",
        "company": {
        "id": 15,
        "name": "Tech Innovations Inc."
        },
        "job_level": "Senior",
        "years_experience": "5+ years",
        "requirements": [
        "5+ years of Python experience",
        "Strong knowledge of Flask/Django",
        "Experience with PostgreSQL",
        "Understanding of RESTful API design"
        ],
        "responsibilities": [
        "Design and implement backend services",
        "Mentor junior developers",
        "Optimize application performance",
        "Write clean, maintainable code"
        ],
        "created_at": "2023-11-15T14:30:22.123456",
        "applicant_count": 3
    }]
    all_applications =[
        {
        "id": 101,
        "name": "John Smith",
        "email": "john.smith@example.com",
        "phone_number": "+1 (555) 123-4567",
        "exp_years": 6,
        "skills": [
            "Python",
            "Flask",
            "Django",
            "PostgreSQL",
            "AWS"
        ],
        "experience": [
            {
            "role": "Senior Developer",
            "company": "TechCorp",
            "years": 3
            },
            {
            "role": "Python Developer",
            "company": "WebSolutions",
            "years": 3
            }
        ],
        "education": {
            "degree": "B.Sc Computer Science",
            "school": "State University"
        },
        "match_score": 0.92
        },
        {
        "id": 102,
        "name": "Maria Garcia",
        "email": "maria.g@example.com",
        "phone_number": "+1 (555) 987-6543",
        "exp_years": 5,
        "skills": [
            "Python",
            "Django",
            "JavaScript",
            "MySQL"
        ],
        "experience": [
            {
            "role": "Backend Developer",
            "company": "DataSystems",
            "years": 5
            }
        ],
        "education": {
            "degree": "M.Sc Software Engineering",
            "school": "Tech Institute"
        },
        "match_score": 0.85
        },
        {
        "id": 103,
        "name": "David Kim",
        "email": "david.kim@example.com",
        "phone_number": "+1 (555) 456-7890",
        "exp_years": 7,
        "skills": [
            "Python",
            "FastAPI",
            "MongoDB",
            "Docker"
        ],
        "experience": [
            {
            "role": "Lead Developer",
            "company": "InnovateCo",
            "years": 4
            },
            {
            "role": "Python Developer",
            "company": "CodeMasters",
            "years": 3
            }
        ],
        "education": {
            "degree": "B.Eng Computer Engineering",
            "school": "Polytechnic University"
        },
        "match_score": 0.78
        }
    ]
    return render_template('job_applicants.html', 
                             job=job, 
                             applicants=all_applications)
@app.route('/view_application/<int:app_id>')
def view_application(app_id):
    # In a real application, you would:
    # 1. Verify the user is logged in as a company
    # 2. Verify this application is for one of their jobs
    # 3. Fetch the application details from your database
    
    # For demo purposes, we'll use the test data
    job = {
        "id": 42,
        "title": "Senior Python Developer",
        "company": {
            "id": 15,
            "name": "Tech Innovations Inc."
        }
    }
    
    # Find the applicant in our test data
    all_applications = [
        {
            "id": 101,
            "name": "John Smith",
            "email": "john.smith@example.com",
            "phone_number": "+1 (555) 123-4567",
            "exp_years": 6,
            "skills": ["Python", "Flask", "Django", "PostgreSQL", "AWS"],
            "experience": [
                {"role": "Senior Developer", "company": "TechCorp", "years": 3},
                {"role": "Python Developer", "company": "WebSolutions", "years": 3}
            ],
            "education": {
                "degree": "B.Sc Computer Science",
                "school": "State University"
            },
            "match_score": 0.92
        },
        {
            "id": 102,
            "name": "Maria Garcia",
            "email": "maria.g@example.com",
            "phone_number": "+1 (555) 987-6543",
            "exp_years": 5,
            "skills": ["Python", "Django", "JavaScript", "MySQL"],
            "experience": [
                {"role": "Backend Developer", "company": "DataSystems", "years": 5}
            ],
            "education": {
                "degree": "M.Sc Software Engineering",
                "school": "Tech Institute"
            },
            "match_score": 0.85
        },
        {
            "id": 103,
            "name": "David Kim",
            "email": "david.kim@example.com",
            "phone_number": "+1 (555) 456-7890",
            "exp_years": 7,
            "skills": ["Python", "FastAPI", "MongoDB", "Docker"],
            "experience": [
                {"role": "Lead Developer", "company": "InnovateCo", "years": 4},
                {"role": "Python Developer", "company": "CodeMasters", "years": 3}
            ],
            "education": {
                "degree": "B.Eng Computer Engineering",
                "school": "Polytechnic University"
            },
            "match_score": 0.78
        }
    ]
    
    applicant = next((app for app in all_applications if app['id'] == app_id), None)
    
    if not applicant:
        flash('Applicant not found', 'error')
        return redirect(url_for('company_dashboard'))
    
    return render_template('view_application.html', 
                         job=job, 
                         applicant=applicant)


### HR ###  
@app.route('/hr_dashboard')
def hr_dashboard():
    return render_template('hr_dashboard.html')

### list of applicant applied to a Job ###
@app.route('/hr_applied_applicant/<int:job_id>')
def hr_view_applied_applicant(job_id): 
    # # Fetch job details --> requirements 
    # job_response = requests.get(f"{DATABASE_URL}/get_offered_jobs/{job_id}")
    # if job_response.status_code != 200:
    #     flash('Error fetching your offeredt jobs', 'error')
    #     return render_template('hr_view_applied_applicant.html', jobs=[])
        
    # job = job_response.json()
    
    # # Fetch applicants for this job --> with his match result
    # applicants_response = requests.get(f"{DATABASE_URL}/get_applied_job/{job_id}")
    # if applicants_response.status_code != 200:
    #     flash('Error fetching your applicant', 'error')
    #     return render_template('hr_view_applied_applicant.html', jobs=[])
    
    # applicants_data = []
    # for application in applicants_response.json():
    #     # Get applicant details
    #     user_response = requests.get(f"{DATABASE_URL}/get_user/{application['applicant_id']}")
    #     if user_response.status_code != 200:
    #         continue
            
    #     user = user_response.json()
        
    #     # Get applicant CV
    #     cv_response = requests.get(f"{DATABASE_URL}/get_applicant/{application['applicant_id']}")
    #     cv = cv_response.json()[0] if cv_response.status_code == 200 and cv_response.json() else None
        
    #    # Use the score from applied_job table
    #     match_score = application.get('scores', 0)
        
    #     applicants_data.append({
    #         'id': user['ID'],
    #         'name': f"{user['first_name']} {user['last_name']}",
    #         'similarity_score': match_score,
    #         'exp_years': cv['experience_years'] if cv else 0,
    #         'email': user['email'],
    #         'phone_number': user['phone_number'],
    #         'skills': cv['skills'].split(',') if cv and cv['skills'] else [],
    #         'status': application['status'],
    #         'meets_threshold': application['meets_threshold'],
    #         'qualified_cv': application['qualified_cv']
    #     })

    job = {
        "id": 101,
        "job_title": "Senior Backend Engineer",
        "job_level": "Mid-Senior",
        "years_experience": 5,
        "date_offering": "2024-12-01",
        "status": "open"
    }

    applicants = [
        {
            "id": 202,
            "name": "Michael Chen",
            "similarity_score": 62,
            "exp_years": 5,
            "email": "michael.c@example.com",
            "phone_number": "+12345550102",
            "skills": ["Java", "Spring", "SQL"],
            "qualified_cv": True,
            "status": "under_review"
        },
        {
            "id": 203,
            "name": "Sara Ibrahim",
            "similarity_score": 45,
            "exp_years": 2,
            "email": "zynab.ahamd.saad@gmail.com",
            "phone_number": "+12345550103",
            "skills": ["HTML", "CSS", "Bootstrap", "JavaScript", "Vue.js"],
            "qualified_cv": False,
            "status": "rejected"
        },
        {
            "id": 204,
            "name": "David O'Connor",
            "similarity_score": 88,
            "exp_years": 7,
            "email": "zynab.ahamd.saad@gmail.com",
            "phone_number": "+12345550104",
            "skills": ["Python", "Django", "PostgreSQL", "Docker"],
            "qualified_cv": True,
            "status": "interview_scheduled"
        }
    ]
    
    return render_template('hr_view_applied_applicant.html', 
                         job=job, 
                         applicants=applicants)




### If match score fit requirement then schedule a meeting ###
@app.route('/schedule_meeting/<int:applicant_id>/<int:job_id>', methods=['GET', 'POST'])
def schedule_meeting(applicant_id, job_id):
    # if 'user_id' not in session:
    #     flash('Please login', 'error')
    #     return redirect(url_for('login'))

    if request.method == 'POST':
        meeting_id = request.form.get('meeting_id', '')
        # meeting_title = request.form['title']
        # meeting_date = request.form['date']
        # start_time = request.form['start_time']
        # end_time = request.form['end_time']
        # Get applicant_id and job_id from form
        form_applicant_id = request.form.get('applicant_id', '')
        form_job_id = request.form.get('job_id', '')
        print(form_job_id)
    
    # Check if we're updating an existing meeting
        if meeting_id:
            print(meeting_id)
            # updated_meeting = {
            # 'meeting_id': meeting_id,
            # 'meeting_title': request.form.get('title', ''),
            # 'meeting_date': request.form.get('date', ''),
            # 'start_time': request.form.get('start_time', ''),
            # 'end_time': request.form.get('end_time', ''),
            # 'applicant_id': request.form.get('applicant_id', ''),
            # 'job_id': request.form.get('job_id', '')
            # }
        
            # # Make the API call to update the meeting in your database
            # update_response = requests.put(f"{DATABASE_URL}/update_interview/{meeting_id}", json=updated_meeting)
            # if update_response.status_code == 200:
            #     print('Meeting updated successfully!')
            #     flash('Meeting updated successfully!', 'success')
            # Update existing meeting
            # In a real app, you would update the meeting in your database
            print('Meeting updated successfully!')
            flash('Meeting updated successfully!', 'success')
        else:
            print("schedule is submitted")
        #    # Create new meeting
        
        #     user_response = requests.get(f"{DATABASE_URL}/get_user/{applicant_id}")
        #     if user_response.status_code != 200:
        #         flash('Error fetching user data', 'error')
        #         return redirect(url_for('schedule_meeting'))
        #     user_data = user_response.json().get('user', {})

        #     offered_job_response = requests.get(f"{DATABASE_URL}/get_aoffered_job/{job_id}")
        #     if  offered_job_response.status_code != 200:
        #         flash('Error fetching job data', 'error')
        #         return redirect(url_for('schedule_meeting'))
        #     offered_job_response = user_response.json().get('', {})

            
        #     # Assume you've extracted this data:
        #     first_name = user_data.get('first_name', '')
        #     last_name = user_data.get('last_name', '')
        #     email = user_data.get('email', '')
        #     job_title =  offered_job_response.get('job_title', '')  
        #     job_level = offered_job_response.get('job_level', '')  
    
    
        #     # Construct a professional message body
        # # Construct email body for in-person interview
        #     email_body = f"""
        #     Dear {first_name} {last_name},

        #     We are pleased to inform you that you have successfully passed the first stage of our hiring process for the position of **{job_title} ({job_level})** at Hirevo.

        #     🎉 **Congratulations!**

        #     We would like to invite you to the next step — an **in-person interview** with our hiring team.

        #     **Interview Details**
        #     - **Title:** {meeting_title}
        #     - **Date:** {meeting_date}
        #     - **Time:** {start_time} - {end_time}
        #     - **Location:** Hirevo Offices, American University of Beirut (AUB), Bliss Street, Beirut, Lebanon

        #     Please make sure to arrive at least 10 minutes early and bring:
        #     - A copy of your resume
        #     - A valid ID for entry

        #     If you have any questions or need to reschedule, please reply to this email or contact us directly.

        #     We look forward to meeting you in person!

        #     Warm regards,  
        #     **Hirevo HR Team**  
        #     hr@hirevo.com
        #     """
        #     job_response = requests.get(f"{DATABASE_URL}/get_offered_job/{job_id}")
        #     if job_response.status_code != 200:
        #         flash('Error fetching job details', 'error')
        #         return redirect(url_for('jobseeker_dashboard'))
                    
        #     job_data = job_response.json().get('job', {})
                    
        #             # check if the status of job is open
        #     if job_data.get('status', '').lower() != 'open':
        #         flash('This job is no longer available', 'error')
        #         return redirect(url_for('jobseeker_dashboard'))
                
        #     cv_response = requests.get(f"{DATABASE_URL}/get_applicant/{applicant_id}")
        #     cv_data = cv_response.json().get('cv_data', {})
        #     generate_question_response = requests.post(
        #                 f"{Interview_Questions_URL}/handle_question_generation",
        #                 json={
        #                     'cv': cv_data,
        #                     'job': job_data
        #                 }
        #             )
            

        #     msg = Message(
        #         subject="You're Invited: Next Step in Your Hirevo Application 🎯",
        #         recipients=[email],
        #         body=email_body
        #     )

        #     save_interview = requests.post(f"{DATABASE_URL}/add_interview", json={
        #         'interview': {
        #             "applicant_id": applicant_id,
        #             "job_id": job_id,
        #             'meeting_title': request.form['title'],
        #             'meeting_date': request.form['date'],
        #             'start_time': request.form['start_time'],
        #             'end_time': request.form['end_time']
        #         },
        #         'questions': generate_question_response
        #     })

        #     mail.send(msg)
        # Redirect to prevent form resubmission
        return redirect(url_for('schedule_meeting', 
                                applicant_id=applicant_id, 
                             job_id=job_id))   
    # get_interview_response = requests.get(f"{DATABASE_URL}/get_interview")

    # if get_interview_response.status_code != 200:
    #         flash('Error fetching interviews', 'error')
    #         return render_template('company_dashboard.html', jobs=[])

    # interviews = get_interview_response.json().get('interviews', [])

    # meeting_data = []

    # for interview in interviews:
    #         applicant_id = interview.get('applicant_id')
    #         job_id = interview.get('job_id')

    #         # Skip if missing data
    #         if not applicant_id or not job_id:
    #             continue

    #         # Get applicant info
    #         user_response = requests.get(f"{DATABASE_URL}/get_user/{applicant_id}")
    #         if user_response.status_code != 200:
    #             continue
    #         user_data = user_response.json()
    #         full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}"

    #         # Get job info
    #         job_response = requests.get(f"{DATABASE_URL}/get_offered_job/{job_id}")
    #         if job_response.status_code != 200:
    #             continue
    #         job_data = job_response.json()
    #         job_title = job_data.get('job_title', 'Unknown Job')

    #         # Append full info per interview
    #         meeting_data.append({
    #             "applicant_name": full_name,
    #             "job_title": job_title,
    #             "meeting_title": interview.get('meeting_title', 'Untitled'),
    #             "meeting_date": interview.get('meeting_date', ''),
    #             "start_time": interview.get('start_time', ''),
    #             "end_time": interview.get('end_time', '')
    #         })
    meeting_data = [
        {
            "applicant_name": "Alice Johnson",
            "job_title": "Frontend Developer",
            "meeting_title": "Frontend Developer Interview",
            "meeting_date": "2025-04-22",
            "start_time": "10:00",
            "end_time": "11:00",
            "applicant_id": "1",  # Make sure to include these IDs
            "job_id": "101"
        },
        {
            "applicant_name": "Bob Smith",
            "job_title": "Backend Developer",
            "meeting_title": "Backend Developer Interview",
            "meeting_date": "2025-04-22",
            "start_time": "12:00",
            "end_time": "13:00",
            "applicant_id": "2",
            "job_id": "102"
        },
        {
            "applicant_name": "Carol Lee",
            "job_title": "UI/UX Designer",
            "meeting_title": "Design Interview",
            "meeting_date": "2025-04-23",
            "start_time": "09:00",
            "end_time": "10:00",
            "applicant_id": "3",
            "job_id": "103"
        }
    ]

    # Send all interview data to the template
    return render_template('schedule_interview.html', meetings=meeting_data, applicant_id=applicant_id,job_id =job_id)




@app.route('/reject-applicant/<int:applicant_id>/<int:job_id>')
def reject_applicant(applicant_id, job_id):
    # try:
    #     # Get applicant details
    #     user_response = requests.get(f"{DATABASE_URL}/get_user/{applicant_id}")
    #     if user_response.status_code != 200:
    #         flash('Error fetching applicant data', 'error')
    #         return redirect(url_for('hr_view_applied_applicant', job_id=job_id))
        
    #     user_data = user_response.json()
    #     first_name = user_data.get('first_name', '')
    #     last_name = user_data.get('last_name', '')
    #     email = user_data.get('email', '')

    #     # Get job details
    #     job_response = requests.get(f"{DATABASE_URL}/get_offered_job/{job_id}")
    #     if job_response.status_code != 200:
    #         flash('Error fetching job data', 'error')
    #         return redirect(url_for('hr_view_applied_applicant', job_id=job_id))
        
    #     job_data = job_response.json()
    #     job_title = job_data.get('job_title', 'the position')
    #     company_name = "Hirevo"  # You might want to fetch this from your database

    #     # Construct rejection email
    #     subject = f"Update on Your Application for {job_title}"
        
    #     email_body = f"""
    #     Dear {first_name} {last_name},

    #     Thank you for taking the time to apply for the {job_title} position at {company_name} 
    #     and for sharing your qualifications with us.

    #     After careful consideration, we regret to inform you that we have decided to move forward 
    #     with other candidates whose qualifications more closely match our current needs.

    #     We genuinely appreciate your interest in {company_name} and the effort you put into your 
    #     application. This decision was not easy to make, as we were impressed with many aspects 
    #     of your background.

    #     We encourage you to apply for future openings that may be a better fit for your skills 
    #     and experience. We'll keep your resume on file and will reach out if any suitable 
    #     opportunities arise.

    #     We wish you the best in your job search and future career endeavors.

    #     Sincerely,
    #     The Hiring Team
    #     {company_name}
    #     hr@{company_name.lower()}.com
    #     """

    #     # Send email (assuming you have Flask-Mail configured)
    #     msg = Message(
    #         subject=subject,
    #         recipients=[email],
    #         body=email_body
    #     )
    #     mail.send(msg)

    #     # Update applicant status in database (optional)
    #     # update_response = requests.put(f"{DATABASE_URL}/update_application_status", json={
    #     #     'applicant_id': applicant_id,
    #     #     'job_id': job_id,
    #     #     'status': 'rejected'
    #     # })

    #     print('Applicant has been rejected', 'success')
    
    #     return redirect(url_for('hr_view_applied_applicant', job_id=job_id, applicants=applicant_id))
    # except Exception as e:
    #     print(f"Error rejecting applicant: {str(e)}")
    #     flash('An error occurred while processing the rejection', 'error')
    #     return redirect(url_for('hr_view_applied_applicant', job_id=job_id))
    
    # Just testing output
    print('Applicant has been rejected', 'success')
    
    return redirect(url_for('hr_view_applied_applicant', job_id=job_id, applicants=applicant_id))


MEETINGS = [
    {
        "id": 123,
        "title": "Product Development Standup",
        "date": "2024-05-22",
        "start_time": "09:00",
        "end_time": "10:00",
        "duration": "1 hour",
        "team": "Team Alpha",
        "location": "Virtual",
        "meeting_type": "Zoom Meeting",
        "status": "upcoming",
        "questions": [
            {"id": 1, "text": "What progress has been made on the new feature implementation?", "priority": "high", "answered": False},
            {"id": 2, "text": "Are there any blockers that need to be addressed?", "priority": "medium", "answered": False},
            {"id": 3, "text": "What is the timeline for the next release?", "priority": "high", "answered": False},
            {"id": 4, "text": "What resources are needed for the upcoming sprint?", "priority": "medium", "answered": False},
            {"id": 5, "text": "How can we improve our development process?", "priority": "low", "answered": False}
        ]
    },
    # Add more meetings here
]

@app.route('/weekly_meeting')
def weekly_meeting():
    return render_template('weekly_meetings.html', meetings=MEETINGS)

@app.route('/meeting/<int:meeting_id>')
def meeting_answers(meeting_id):
    meeting = next((m for m in MEETINGS if m["id"] == meeting_id), None)
    if not meeting:
        return redirect(url_for('index'))
    return render_template('meeting_answers.html', meeting=meeting)   

### Offered Job List ###
@app.route('/offered_job')
def offered_job():
    # if 'user_id' not in session:
    #     flash('Please login', 'error')
    #     return redirect(url_for('login'))
    
    # try:
    #     # Get jobs posted by department
    #     hr_id = session['user_id']
    #     job_offere_response = requests.get(f"{DATABASE_URL}/get_offered_job")
        
    #     if job_offere_response.status_code != 200:
    #         flash('Error fetching your department jobs', 'error')
    #         return render_template('company_dashboard.html', jobs=[])
        
    #     jobs = job_offere_response.json().get('jobs', [])

    #     job_ids = [job['ID'] for job in jobs]

    #   # get name of the department based on department id
    #     for job in jobs:
    #         dept_id = job['dept_id']
    #         dept_response = requests.get(f"{DATABASE_URL}/get_department/{dept_id}")
    #         dept_response.raise_for_status()
    #         department = dept_response.json().get('department', [])
    #         job['department_name'] = department['department_name']
    #     return render_template('jobseeker_dashboard.html', jobs=jobs)
    
    # except Exception as e:
    #     flash(f'Error loading dashboard: {str(e)}', 'error')
    #     return render_template('jobseeker_dashboard.html', jobs=[])
    
    jobs = [
    {
        "id": 1,
        "job_title": "Senior Software Engineer",
        "job_id": "#JOB-001",
        "department_name": "Engineering",
        "job_level": "Senior Level",
        "years_experience": "5+ years experience",
        "status": "Open",
        "date_offering": "May 15, 2024",
        "requirements": [
            "Bachelor's degree in Computer Science or related field",
            "5+ years of experience in software development",
            "Proficiency in JavaScript, TypeScript, and React",
            "Experience with cloud platforms (AWS, Azure, GCP)",
            "Strong problem-solving skills and attention to detail"
        ],
        "responsibilities": [
            "Design and implement new features for our web applications",
            "Collaborate with cross-functional teams to define requirements",
            "Write clean, maintainable, and efficient code",
            "Perform code reviews and mentor junior developers",
            "Troubleshoot and debug issues in production environments"
        ],
        "required_certifications": [
            "AWS Certified Developer (preferred)",
            "Google Cloud Professional Developer (preferred)"
        ],
        "applicants": 12
    },
    {
        "id": 2,
        "job_title": "Marketing Specialist",
        "job_id": "#JOB-002",
        "department_name": "Marketing",
        "job_level": "Mid Level",
        "years_experience": "3-5 years experience",
        "status": "Open",
        "date_offering": "May 10, 2024",
        "requirements": [
            "Bachelor's degree in Marketing, Communications, or related field",
            "3-5 years of experience in digital marketing",
            "Proficiency in social media platforms and analytics tools",
            "Experience with content creation and campaign management",
            "Strong communication and analytical skills"
        ],
        "responsibilities": [
            "Develop and implement marketing strategies",
            "Create engaging content for various platforms",
            "Manage social media accounts and campaigns",
            "Analyze marketing metrics and prepare reports",
            "Collaborate with design and sales teams"
        ],
        "required_certifications": [
            "Google Analytics Certification",
            "HubSpot Content Marketing Certification (preferred)"
        ],
        "applicants": 8
    },
    {
        "id": 3,
        "job_title": "Sales Representative",
        "job_id": "#JOB-003",
        "department_name": "Sales",
        "job_level": "Entry Level",
        "years_experience": "0-1 years experience",
        "status": "Open",
        "date_offering": "May 18, 2024",
        "requirements": [
            "Bachelor's degree in Business, Marketing, or related field",
            "0-1 years of experience in sales (internships count)",
            "Excellent communication and interpersonal skills",
            "Self-motivated with a strong desire to succeed",
            "Ability to work in a fast-paced environment"
        ],
        "responsibilities": [
            "Generate leads and build relationships with potential clients",
            "Conduct product demonstrations and presentations",
            "Meet or exceed sales targets",
            "Maintain accurate records in CRM system",
            "Collaborate with marketing and product teams"
        ],
        "required_certifications": [
            "No specific certifications required"
        ],
        "applicants": 15
    },
    {
        "id": 4,
        "job_title": "HR Specialist",
        "job_id": "#JOB-004",
        "department_name": "Human Resources",
        "job_level": "Mid Level",
        "years_experience": "3-5 years experience",
        "status": "Closed",
        "date_offering": "April 25, 2024",
        "requirements": [
            "Bachelor's degree in Human Resources, Business, or related field",
            "3-5 years of experience in HR",
            "Knowledge of HR practices, policies, and employment laws",
            "Experience with HRIS systems",
            "Strong interpersonal and communication skills"
        ],
        "responsibilities": [
            "Develop and implement HR policies and procedures",
            "Manage recruitment and onboarding processes",
            "Handle employee relations and performance management",
            "Maintain employee records and ensure legal compliance",
            "Provide HR support to employees and managers"
        ],
        "required_certifications": [
            "PHR or SHRM-CP certification (preferred)"
        ],
        "applicants": 6
    },
    
]

    return render_template('offered_job.html', jobs=jobs)  
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  
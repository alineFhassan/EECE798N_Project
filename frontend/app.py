from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import os
from datetime import datetime

app = Flask(__name__)
# To be Changes 
app.secret_key = 'dev-key-123-abc!@#'

DATABASE_URL = os.getenv('DATABASE_URL', 'http://database:5002')
CV_JOB_MATCHER_URL = os.getenv('CV_JOB_MATCHER_URL', 'http://cv-job-matcher:5003')
JOB_GENERATOR_URL = os.getenv('JOB_GENERATOR_URL', 'http://job-generator:5004')


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
                        f"{DATABASE_URL}/add_applicantion",
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
            f"{DATABASE_URL}/applications/{session['user_id']}"
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
        response = requests.get(f"{DATABASE_URL}/get_job")
        if response.status_code != 200:
            flash('Error fetching jobs', 'error')
            return render_template('jobseeker_dashboard.html', jobs=[])
        
        jobs = response.json().get('jobs', [])

        # Filter only open jobs
        open_jobs = [job for job in jobs if job.get('status', '').lower() == 'open']

        # get name of the department based on department id
        for job in open_jobs:
            dept_id = job['dept_id']
            dept_response = requests.get(f"{DATABASE_URL}/department/{dept_id}")
            dept_response.raise_for_status()
            department = dept_response.json().get('department', [])
            job['department_name'] = department['department_name']
        
        # Check if user has uploaded CV
        cv_response = requests.get(f"{DATABASE_URL}/applications/{session['user_id']}")
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
                job_response = requests.get(f"{DATABASE_URL}/get_job/{job_id}")
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
                    f"{DATABASE_URL}/apply_job",
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
        job_offere_response = requests.get(f"{DATABASE_URL}/get_job/{dept_id}")
        
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
        job_offere_response = requests.get(f"{DATABASE_URL}/get_job/{dept_id}")
        
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
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 
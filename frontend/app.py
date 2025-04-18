from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import os

app = Flask(__name__)
# To be Changes 
app.secret_key = 'dev-key-123-abc!@#'

DATABASE_URL = os.getenv('DATABASE_URL', 'http://database:5003')
CV_JOB_MATCHER_URL = os.getenv('CV_JOB_MATCHER_URL', 'http://cv-job-matcher:5004')


# Main Dashboard
@app.route('/')
def index():
    return render_template('index.html')

### Login ###
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
                    if data.get('register_option') == 'company' and data.get('user_id') == 1 :
                        return redirect(url_for('hr_dashboard'))
                    elif data.get('register_option') == 'company':
                        return redirect(url_for('company_dashboard'))
                    else:
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

        if password != confirm_password:
            flash('Passwords do not match', 'error')
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

# Upload CV
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

### Jobseeker dashboard ###
@app.route('/jobseeker_dashboard', methods=['GET', 'POST'])
def jobseeker_dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    try:
        # Get all jobs from database
        response = requests.get(f"{DATABASE_URL}/get_job")
        if response.status_code != 200:
            flash('Error fetching jobs', 'error')
            return render_template('jobseeker_dashboard.html', jobs=[])
        
        jobs = response.json().get('jobs', [])

        # get name of the department based on department id
        for job in jobs:
            dept_id = job['dept_id']
            dept_response = requests.get(f"{DATABASE_URL}/department/{dept_id}")
            dept_response.raise_for_status()
            department = dept_response.json()
            job['department_name'] = department['department_name']

        # If user apply for a Job 
        if request.method == 'POST':
            job_id = request.form.get('job_id')

            if job_id:
                # Get job details
                job_response = requests.get(f"{DATABASE_URL}/get_job/{job_id}")
                if job_response.status_code == 200:
                    job_data = job_response.json().get('job', {})
                    
                # Get CV data
                cv_response = requests.get(f"{DATABASE_URL}/get_cv/{session['user_id']}")
                if cv_response.status_code == 200:
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
                        'user_id': session['user_id'],
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
        
        return render_template('jobseeker_dashboard.html', jobs=jobs)
    
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('jobseeker_dashboard.html', jobs=[])

# company
@app.route('/company_dashboard')
def company_dashboard():
    # if 'user_id' not in session or session.get('user_type') != 'company':
    #     flash('Please login as a company first', 'error')
    #     return redirect(url_for('login'))
    
    # try:
    #     # Get jobs posted by this company
    #     company_id = session['user_id']
    #     response = requests.get(f"{DATABASE_URL}/job?company_id={company_id}")
        
    #     if response.status_code != 200:
    #         flash('Error fetching your company jobs', 'error')
    #         return render_template('company_dashboard.html', jobs=[])
        
    #     jobs = response.json().get('jobs', [])
        
    #     # Count stats for the dashboard
    #     active_jobs = len(jobs)
    #     total_applicants = sum(job.get('applicant_count', 0) for job in jobs)
        
    #     return render_template('company_dashboard.html', 
    #                         jobs=jobs[:3],  # Show only 3 most recent
    #                         active_jobs=active_jobs,
    #                         total_applicants=total_applicants)
    
    # except Exception as e:
    #     flash(f'Error loading dashboard: {str(e)}', 'error')
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
        }
    ]
    
        # return render_template('company_dashboard.html', jobs=[])
    return render_template('company_dashboard.html', jobs=jobs)
from datetime import datetime

@app.template_filter('format_date')
def format_date_filter(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
        return date_obj.strftime('%b %d, %Y')
    except:
        return date_str
    
@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    # if 'user_id' not in session or session.get('user_type') != 'company':
    #     flash('Please login as a company first', 'error')
    #     return redirect(url_for('login'))
    
    # if request.method == 'POST':
    #     try:
    #         # Get form data
              # job_title / job_ level / yeras_experience / addational_json
    #         job_data = {
    #             'title': request.form.get('jobTitle'),
    #             'description': request.form.get('jobDescription'),
    #             'company_id': session['user_id'],
    #             'job_level': request.form.get('jobLevel'),
    #             'years_experience': request.form.get('yearsExperience'),
    #             'responsibilities': request.form.getlist('responsibilities'),
    #             'requirements': request.form.getlist('requirements')
    #         }
            

    #         # Send to database service
    #         response = requests.post(
    #             f"{DATABASE_URL}/job",
    #             json=job_data
    #         )

    #         if response.status_code == 201:
    #             flash('Job posted successfully!', 'success')
    #             return redirect(url_for('company_dashboard'))
    #         else:
    #             flash('Error posting job: ' + response.json().get('message', ''), 'error')
        
    #     except Exception as e:
    #         flash('Error: ' + str(e), 'error')
    
    return render_template('post_job.html')

@app.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    # if 'user_id' not in session or session.get('user_type') != 'company':
    #     flash('Please login as a company first', 'error')
    #     return redirect(url_for('login'))
    
    # try:
    #     if request.method == 'GET':
    #         # Fetch existing job data
    #         response = requests.get(f"{DATABASE_URL}/jobs/{job_id}")
            
    #         if response.status_code != 200:
    #             flash('Job not found', 'error')
    #             return redirect(url_for('company_dashboard'))
            
    #         job = response.json().get('job')
            
    #         # Verify this company owns the job
    #         if job['company_id'] != session['user_id']:
    #             flash('You can only edit your own jobs', 'error')
    #             return redirect(url_for('company_dashboard'))
            
    #         return render_template('edit_job.html', job=job)
        
    #     elif request.method == 'POST':
    #         # Process form submission
    #         job_data = {
    #             'title': request.form.get('jobTitle'),
    #             'description': request.form.get('jobDescription'),
    #             'job_level': request.form.get('jobLevel'),
    #             'years_experience': request.form.get('yearsExperience'),
    #             'responsibilities': request.form.getlist('responsibilities'),
    #             'requirements': request.form.getlist('requirements')
    #         }
            
    #         # Send update to database
    #         response = requests.put(
    #             f"{DATABASE_URL}/jobs/{job_id}",
    #             json=job_data
    #         )
            
    #         if response.status_code == 200:
    #             flash('Job updated successfully!', 'success')
    #             return redirect(url_for('company_dashboard'))
    #         else:
    #             flash('Error updating job: ' + response.json().get('message', ''), 'error')
    #             return redirect(url_for('edit_job', job_id=job_id))
    
    # except Exception as e:
    #     flash(f'Error: {str(e)}', 'error')
    #     return redirect(url_for('company_dashboard'))

    # to test
      # Test job data - properly structured
    test_job = {
        "id": job_id,  # Use the provided job_id
        "title": "Senior Python Developer",
        "description": "We're looking for an experienced Python developer...",
        "company_id": 15,
        "job_level": "Senior",
        "years_experience": "5+ years",
        "responsibilities": [
            "Design and implement backend services",
            "Mentor junior developers",
            "Write clean, maintainable code"
        ],
        "requirements": [
            "5+ years of Python experience",
            "Strong knowledge of Flask/Django",
            "Experience with PostgreSQL"
        ],
        "created_at": "2023-11-15T14:30:22.123456",
        "company": {
            "id": 15,
            "name": "Tech Innovations Inc."
        },
        "applicant_count": 8
    }
    
    return render_template('edit_job.html', job=test_job)


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

# CV-Job Matching 
# GET /jobs/{job_id} - Get job details
# GET /get_unmatched_applications?job_id=X - Returns only applicants without existing matches
# POST /save_match_result - Saves matching results
@app.route('/calculate_matches/<int:job_id>', methods=['POST'])
def calculate_matches(job_id):
    # Authentication check (uncomment in production)
    # if 'user_id' not in session or session.get('user_type') != 'hr':
    #     flash('Please login as HR first', 'error')
    #     return redirect(url_for('login'))

    try:
        # 1. Get job details
        job_response = requests.get(f"{DATABASE_URL}/jobs/{job_id}")
        if job_response.status_code != 200:
            flash('Job not found', 'error')
            return redirect(url_for('hr_dashboard'))
        job = job_response.json().get('job')

        # 2. Get all applicants for this job who haven't been matched yet
        applications_response = requests.get(
            f"{DATABASE_URL}/get_unmatched_applications?job_id={job_id}"
        )
        
        if applications_response.status_code != 200:
            flash('Error fetching applications', 'error')
            return redirect(url_for('hr_dashboard'))
            
        applicants = applications_response.json().get('applications', [])
        
        if not applicants:
            flash('No new applicants to process', 'info')
            return redirect(url_for('view_job_matches', job_id=job_id))

        # 3. Process matching for each unmatched applicant
        processed = 0
        for applicant in applicants:
            try:
                # Skip if already has match data (safety check)
                if applicant.get('match_data'):
                    continue

                # Prepare matching data
                match_payload = {
                    'cv': {
                        'skills': applicant.get('skills', []),
                        'education': applicant.get('education', ''),
                        'responsibilities': applicant.get('responsibilities', []),
                        'years_experience': applicant.get('exp_years', 0),
                        # Add other CV fields you extract
                    },
                    'job': {
                        'title': job['title'],
                        'requirements': job['requirements'],
                        'responsibilities': job['responsibilities'],
                        'required_experience_years': int(job['years_experience'].split('+')[0]) 
                        # Extracts number from "5+ years" format
                    }
                }

                # Call matching service
                match_response = requests.post(
                    f"{CV_JOB_MATCHER_URL}/cv-job-match",
                    json=match_payload,
                    timeout=10  # 10 seconds timeout
                )
                match_response.raise_for_status()

                # Save results to database
                save_response = requests.post(
                    f"{DATABASE_URL}/save_match_result",
                    json={
                        'application_id': applicant['id'],
                        'job_id': job_id,
                        'match_data': match_response.json().get('result')
                    }
                )
                save_response.raise_for_status()

                processed += 1

            except requests.exceptions.RequestException as e:
                # Log error but continue with next applicant
                app.logger.error(f"Error processing applicant {applicant['id']}: {str(e)}")
                continue

        # 4. Show results
        if processed > 0:
            flash(f'Successfully processed matches for {processed} applicants', 'success')
        else:
            flash('No new applicants were processed', 'info')

        return redirect(url_for('view_job_matches', job_id=job_id))

    except Exception as e:
        flash(f'Error in matching process: {str(e)}', 'error')
        return redirect(url_for('hr_dashboard'))
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 
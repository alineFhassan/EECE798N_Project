from flask import Flask, request, jsonify
import psycopg2
import os
import json
import requests
import numpy as np


app = Flask(__name__)

# Database connection parameters
DB_HOST = 'host.docker.internal'
DB_PORT = '5433'  # Map to your Docker container's port
DB_NAME = 'jobmatch'
DB_USER = 'postgres'
DB_PASSWORD = 'password'

def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn


@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        date_of_birth = data.get('date')  # Frontend sends 'date' but schema expects 'date_of_birth'
        password = data.get('password')
        user_type = data.get('user_type', 'applicant')  # Default to 'applicant' if not provided

        # Validate required fields
        if not all([first_name, last_name, email, phone_number, date_of_birth, password]):
            return jsonify({"status": "error", "message": "All fields are required."}), 400

        # Hash the password (use a secure hashing method)
        # For example, using bcrypt:
        # hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Email already registered."}), 409

        # Insert the new user
        cursor.execute("""
            INSERT INTO users (first_name, last_name, email, password, date_of_birth, phone_number, user_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (first_name, last_name, email, password, date_of_birth, phone_number, user_type))  # Use hashed_password here

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "User registered successfully."}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# login route
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')  # In production, compare hashed passwords
        register_option = data.get('register_option')  # This is the user_type from the frontend

        if not email or not password or not register_option:
            return jsonify({"status": "error", "message": "All fields are required."}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check different tables based on register_option
        if register_option == 'company':
            # Check in departments table
            cursor.execute("""
                SELECT id, email, name FROM departments 
                WHERE email = %s AND password = %s;
            """, (email, password))
            
            user = cursor.fetchone()
            
            if user:
                cursor.close()
                conn.close()
                return jsonify({
                    "status": "success",
                    "user_id": user[0],
                    "register_option": "company"
                }), 200
        else:
            # Check in users table
            cursor.execute("""
                SELECT id, email, user_type FROM users 
                WHERE email = %s AND password = %s;
            """, (email, password))
            
            user = cursor.fetchone()
            
            if user:
                cursor.close()
                conn.close()
                return jsonify({
                    "status": "success",
                    "user_id": user[0],
                    "register_option": user[2]  # Return user_type as register_option
                }), 200

        # If we get here, no user was found
        cursor.close()
        conn.close()
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    


@app.route('/check_db', methods=['GET'])
def check_db():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "success", "message": "Database connection successful!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, full_name, username, email, user_type FROM users;")
        users = cursor.fetchall()

        # Format the result as a list of dictionaries
        users_list = []
        for user in users:
            users_list.append({
                "id": user[0],
                "full_name": user[1],
                "username": user[2],
                "email": user[3],
                "user_type": user[4]
            })

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "users": users_list}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
 
    

@app.route('/add_applicant', methods=['POST'])
def add_application():
    try:
        data = request.json
        cv_data = data.get('cv_data', {})
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"status": "error", "message": "User ID is required."}), 400

        # Extract fields from cv_data
        education = json.dumps(cv_data.get('education', []))
        skills = json.dumps(cv_data.get('skills', []))
        experience = json.dumps(cv_data.get('experience', []))
        projects = json.dumps(cv_data.get('projects', []))
        certifications = json.dumps(cv_data.get('certifications', []))
        
        # Calculate total experience years
        experience_years = sum(
            exp.get('years', 0) 
            for exp in cv_data.get('experience', []) 
            if isinstance(exp.get('years', 0), (int, float))
        )

        # Database insertion
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user already has a CV
        cursor.execute("SELECT id FROM applicant_cv WHERE user_id = %s", (user_id,))
        existing_cv = cursor.fetchone()

        if existing_cv:
            # Update existing CV
            cursor.execute("""
                UPDATE applicant_cv 
                SET education = %s, skills = %s, experience = %s, 
                    experience_years = %s, projects = %s, certifications = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s;
            """, (
                education, skills, experience, experience_years, 
                projects, certifications, user_id
            ))
            message = "CV updated successfully."
        else:
            # Insert new CV
            cursor.execute("""
                INSERT INTO applicant_cv (
                    user_id, education, skills, experience, 
                    experience_years, projects, certifications
                ) VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                user_id, education, skills, experience, 
                experience_years, projects, certifications
            ))
            message = "CV added successfully."

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": message}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_applicant/<int:user_id>', methods=['GET'])
def get_applicant_cv(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get CV data for the specific user
        cursor.execute("""
            SELECT id, education, skills, experience, 
                   experience_years, projects, certifications,
                   created_at, updated_at
            FROM applicant_cv
            WHERE user_id = %s;
        """, (user_id,))
        
        cv = cursor.fetchone()
        
        if not cv:
            return jsonify({"status": "error", "message": "CV not found"}), 404
            
        # Format the result as a dictionary that matches the frontend's expected format
        cv_data = {
            "education": json.loads(cv[1]) if cv[1] else [],
            "skills": json.loads(cv[2]) if cv[2] else [],
            "experience": json.loads(cv[3]) if cv[3] else [],
            "experience_years": json.loads(cv[4] if cv[4] else None),
            "projects": json.loads(cv[5]) if cv[5] else [],
            "certifications": json.loads(cv[6]) if cv[6] else []
        }

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "cv_data": cv_data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user data
        cursor.execute("""
            SELECT id, first_name, last_name, email, 
                   phone_number, date_of_birth
            FROM users
            WHERE id = %s;
        """, (user_id,))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
            
        # Format the result as a dictionary
        user_data = {
            "id": user[0],
            "first_name": user[1],
            "last_name": user[2],
            "email": user[3],
            "phone_number": user[4],
            "date_of_birth": user[5].isoformat() if user[5] else None
        }

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "user": user_data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/get_offered_job', methods=['GET'])
def get_offered_jobs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get all jobs with department information
        cursor.execute("""
            SELECT j.id, j.title, j.job_level, j.years_experience, 
                   j.requirements, j.responsibilities, j.required_certifications,
                   j.status, j.date_offered, j.created_at, j.department_id,
                   d.name as department_name
            FROM jobs j
            JOIN departments d ON j.department_id = d.id
            ORDER BY j.created_at DESC;
        """)
        
        jobs = []
        for job in cursor.fetchall():
            jobs.append({
                "id": job[0],
                "title": job[1],
                "job_level": job[2],
                "years_experience": job[3],
                "requirements": json.loads(job[4]) if job[4] else [],
                "responsibilities": json.loads(job[5]) if job[5] else [],
                "required_certifications": json.loads(job[6]) if job[6] else [],
                "status": job[7],
                "date_offered": job[8].isoformat() if job[8] else None,
                "created_at": job[9].isoformat() if job[9] else None,
                "dept_id": job[10],
                "department_name": job[11]
            })

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "jobs": jobs}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_offered_job/<int:job_id>', methods=['GET'])
def get_offered_job(job_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get a specific job with department information
        cursor.execute("""
            SELECT j.id, j.title, j.job_level, j.years_experience, 
                   j.requirements, j.responsibilities, j.required_certifications,
                   j.status, j.date_offered, j.created_at, j.department_id,
                   d.name as department_name
            FROM jobs j
            JOIN departments d ON j.department_id = d.id
            WHERE j.id = %s;
        """, (job_id,))
        
        job = cursor.fetchone()
        
        if not job:
            return jsonify({"status": "error", "message": "Job not found"}), 404
            
        job_data = {
            "id": job[0],
            "title": job[1],
            "job_level": job[2],
            "years_experience": job[3],
            "requirements": json.loads(job[4]) if job[4] else [],
            "responsibilities": json.loads(job[5]) if job[5] else [],
            "required_certifications": json.loads(job[6]) if job[6] else [],
            "status": job[7],
            "date_offered": job[8].isoformat() if job[8] else None,
            "created_at": job[9].isoformat() if job[9] else None,
            "dept_id": job[10],
            "department_name": job[11]
        }

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "job": job_data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_department/<int:dept_id>', methods=['GET'])
def get_department(dept_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get department details
        cursor.execute("""
            SELECT id, name, email, created_at
            FROM departments
            WHERE id = %s;
        """, (dept_id,))
        
        dept = cursor.fetchone()
        
        if not dept:
            return jsonify({"status": "error", "message": "Department not found"}), 404
            
        dept_data = {
            "id": dept[0],
            "department_name": dept[1],
            "email": dept[2],
            "created_at": dept[3].isoformat() if dept[3] else None
        }

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "department": dept_data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/add_applied_job', methods=['POST'])
def add_applied_job():
    try:
        data = request.json
        required_fields = ['applicant_id', 'job_id', 'status', 'result']
        
        # Validate required fields
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if job exists and is open
        cursor.execute("""
            SELECT status FROM jobs 
            WHERE id = %s;
        """, (data['job_id'],))
        
        job = cursor.fetchone()
        if not job:
            return jsonify({"status": "error", "message": "Job not found"}), 404
            
        if job[0].lower() != 'open':
            return jsonify({"status": "error", "message": "This job is no longer available"}), 400

        # Check if user has already applied for this job
        cursor.execute("""
            SELECT id FROM applied_jobs 
            WHERE applicant_id = %s AND job_id = %s;
        """, (data['applicant_id'], data['job_id']))
        
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "You have already applied for this job"}), 400

        # Insert the application
        cursor.execute("""
            INSERT INTO applied_jobs (
                applicant_id, job_id, status, scores, 
                thresholds, meets_threshold, passed_criteria, 
                qualified_cv, reason
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            data['applicant_id'],
            data['job_id'],
            data['status'],
            json.dumps(data['result'].get('scores', {})),
            json.dumps(data['result'].get('thresholds', {})),
            json.dumps(data['result'].get('meets_threshold', {})),
            data['result'].get('passed_criteria', ''),
            data['result'].get('qualified_cv', False),
            data['result'].get('reason', '')
        ))

        application_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Application submitted successfully",
            "application_id": application_id
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
@app.route('/get_all_applicants/<job_ids>', methods=['POST'])
def get_all_applicants(job_ids):
    try:
        # Convert job_ids string to list of integers
        job_id_list = [int(id) for id in job_ids.strip('[]').split(',') if id.strip()]
        
        if not job_id_list:
            return jsonify({"status": "error", "message": "No job IDs provided"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get applicants with their application details and CV information
        cursor.execute("""
            SELECT 
                aj.id as application_id,
                aj.applicant_id,
                aj.job_id,
                aj.status as application_status,
                aj.scores,
                aj.thresholds,
                aj.meets_threshold,
                aj.passed_criteria,
                aj.qualified_cv,
                aj.reason,
                aj.created_at as application_date,
                u.first_name,
                u.last_name,
                u.email,
                u.phone_number,
                ac.education,
                ac.skills,
                ac.experience,
                ac.experience_years,
                ac.projects,
                ac.certifications,
                j.title as job_title,
                j.job_level,
                j.years_experience as required_years,
                d.name as department_name
            FROM applied_jobs aj
            JOIN users u ON aj.applicant_id = u.id
            LEFT JOIN applicant_cv ac ON u.id = ac.user_id
            JOIN jobs j ON aj.job_id = j.id
            JOIN departments d ON j.department_id = d.id
            WHERE aj.job_id = ANY(%s)
            ORDER BY aj.created_at DESC;
        """, (job_id_list,))
        
        applicants = []
        for row in cursor.fetchall():
            applicant = {
                "application_id": row[0],
                "applicant_id": row[1],
                "job_id": row[2],
                "application_status": row[3],
                "scores": json.loads(row[4]) if row[4] else {},
                "thresholds": json.loads(row[5]) if row[5] else {},
                "meets_threshold": json.loads(row[6]) if row[6] else {},
                "passed_criteria": row[7],
                "qualified_cv": row[8],
                "reason": row[9],
                "application_date": row[10].isoformat() if row[10] else None,
                "applicant": {
                    "first_name": row[11],
                    "last_name": row[12],
                    "email": row[13],
                    "phone_number": row[14]
                },
                "cv": {
                    "education": json.loads(row[15]) if row[15] else [],
                    "skills": json.loads(row[16]) if row[16] else [],
                    "experience": json.loads(row[17]) if row[17] else [],
                    "experience_years": row[18],
                    "projects": json.loads(row[19]) if row[19] else [],
                    "certifications": json.loads(row[20]) if row[20] else []
                },
                "job": {
                    "title": row[21],
                    "job_level": row[22],
                    "required_years": row[23],
                    "department_name": row[24]
                }
            }
            applicants.append(applicant)

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "applicants": applicants}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/add_interview', methods=['POST'])
def add_interview():
    try:
        data = request.json
        required_fields = ['interview', 'questions']
        
        # Validate required fields
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
            
        interview_data = data['interview']
        questions_data = data['questions']
        
        # Validate interview data
        interview_required_fields = ['applicant_id', 'job_id', 'meeting_title', 'meeting_date', 'start_time', 'end_time']
        if not all(field in interview_data for field in interview_required_fields):
            return jsonify({"status": "error", "message": "Missing required interview fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if applicant exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (interview_data['applicant_id'],))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Applicant not found"}), 404

        # Check if job exists and is open
        cursor.execute("SELECT status FROM jobs WHERE id = %s", (interview_data['job_id'],))
        job = cursor.fetchone()
        if not job:
            return jsonify({"status": "error", "message": "Job not found"}), 404
            
        if job[0].lower() != 'open':
            return jsonify({"status": "error", "message": "This job is no longer available"}), 400

        # Check if interview already scheduled for this time slot
        cursor.execute("""
            SELECT id FROM interviews 
            WHERE applicant_id = %s AND job_id = %s AND date = %s AND start_time = %s;
        """, (
            interview_data['applicant_id'], 
            interview_data['job_id'], 
            interview_data['meeting_date'], 
            interview_data['start_time']
        ))
        
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "An interview is already scheduled for this time slot"}), 400

        # Insert the interview
        cursor.execute("""
            INSERT INTO interviews (
                applicant_id, job_id, meeting_title, date, 
                start_time, end_time, questions
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            interview_data['applicant_id'],
            interview_data['job_id'],
            interview_data['meeting_title'],
            interview_data['meeting_date'],
            interview_data['start_time'],
            interview_data['end_time'],
            json.dumps(questions_data)
        ))

        interview_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Interview scheduled successfully",
            "interview_id": interview_id
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
#Create Job
@app.route('/job', methods=['POST'])
def create_job():
    try:
        data = request.json
        required_fields = ['title', 'description', 'company_id', 'job_level', 'years_experience']
        
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        # Generate job embedding
        embedding_text = f"{data['title']} {data['description']} {data['job_level']}"
        embedding = get_embedding(embedding_text)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO jobs (
                title, description, company_id, 
                job_level, years_experience,
                responsibilities, requirements, 
                created_at, embedding
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            RETURNING id
        """, (
            data['title'],
            data['description'],
            data['company_id'],
            data['job_level'],
            data['years_experience'],
            json.dumps(data.get('responsibilities', [])),
            json.dumps(data.get('requirements', [])),
            json.dumps(embedding)  # Serialize embedding
        ))
        
        job_id = cursor.fetchone()[0]
        conn.commit()
        
        return jsonify({
            "status": "success",
            "job_id": job_id,
            "message": "Job created successfully"
        }), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

#GEt all jobs
@app.route('/job', methods=['GET'])
def get_all_jobs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT j.id, j.title, j.description, j.job_level, j.years_experience,
                   j.responsibilities, j.requirements, j.created_at,
                   u.id as company_id, u.full_name as company_name
            FROM jobs j
            JOIN users u ON j.company_id = u.id
        """)
        
        jobs = []
        for job in cursor.fetchall():
            jobs.append({
                "id": job[0],
                "title": job[1],
                "description": job[2],
                "job_level": job[3],
                "years_experience": job[4],
                "responsibilities": job[5],
                "requirements": job[6],
                "created_at": job[7].isoformat(),
                "company": {
                    "id": job[8],
                    "name": job[9]
                }
            })

        return jsonify({"status": "success", "jobs": jobs}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

#Get specific job
@app.route('/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT j.id, j.title, j.description, j.job_level, j.years_experience,
                   j.responsibilities, j.requirements, j.created_at,
                   u.id as company_id, u.full_name as company_name
            FROM jobs j
            JOIN users u ON j.company_id = u.id
            WHERE j.id = %s
        """, (job_id,))
        
        job = cursor.fetchone()
        if not job:
            return jsonify({"status": "error", "message": "Job not found"}), 404

        return jsonify({
            "status": "success",
            "job": {
                "id": job[0],
                "title": job[1],
                "description": job[2],
                "job_level": job[3],
                "years_experience": job[4],
                "responsibilities": job[5],
                "requirements": job[6],
                "created_at": job[7].isoformat(),
                "company": {
                    "id": job[8],
                    "name": job[9]
                }
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

#UPdate job
@app.route('/jobs/<int:job_id>', methods=['PUT'])
def update_job(job_id):
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # First check if job exists
        cursor.execute("SELECT id FROM jobs WHERE id = %s", (job_id,))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Job not found"}), 404

        # Build dynamic update query
        updates = []
        params = []
        fields = {
            'title': data.get('title'),
            'description': data.get('description'),
            'job_level': data.get('job_level'),
            'years_experience': data.get('years_experience'),
            'responsibilities': json.dumps(data.get('responsibilities')) if 'responsibilities' in data else None,
            'requirements': json.dumps(data.get('requirements')) if 'requirements' in data else None
        }

        for field, value in fields.items():
            if value is not None:
                updates.append(f"{field} = %s")
                params.append(value)

        if not updates:
            return jsonify({"status": "error", "message": "No valid fields to update"}), 400

        params.append(job_id)
        query = f"""
            UPDATE jobs 
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE id = %s
        """
        
        cursor.execute(query, params)
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Job updated successfully"
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

#Delete Job
@app.route('/jobs/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM jobs WHERE id = %s RETURNING id", (job_id,))
        deleted_id = cursor.fetchone()
        
        if not deleted_id:
            return jsonify({"status": "error", "message": "Job not found"}), 404
            
        conn.commit()
        return jsonify({
            "status": "success",
            "message": "Job deleted successfully"
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/match_jobs/<int:application_id>', methods=['GET'])
def match_jobs(application_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Get application's experience and embedding
        cursor.execute("""
            SELECT exp_years, embedding
            FROM application
            WHERE id = %s
        """, (application_id,))
        app_data = cursor.fetchone()
        
        if not app_data:
            return jsonify({"status": "error", "message": "Application not found"}), 404

        exp_years, app_embedding = app_data

        # 2. Find matching jobs using pgvector's native operations
        cursor.execute("""
            SELECT 
                j.id,
                j.title,
                j.description,
                j.company_id,
                1 - (j.embedding <=> a.embedding) AS similarity_score
            FROM jobs j, application a
            WHERE 
                j.years_experience <= %s
                AND a.id = %s
            ORDER BY similarity_score DESC
            LIMIT 10
        """, (exp_years, application_id))
        
        matches = []
        for job in cursor.fetchall():
            matches.append({
                "job_id": job[0],
                "title": job[1],
                "description": job[2],
                "company_id": job[3],
                "similarity_score": float(job[4])
            })

        return jsonify({
            "status": "success",
            "application_id": application_id,
            "matches": matches,
            "experience_filter": exp_years
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/interviews', methods=['GET'])
def get_interviews():
    try:
        user_id = request.args.get('user_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM interview"
        params = ()
        
        if user_id:
            query += " WHERE user_id = %s"
            params = (user_id,)

        cursor.execute(query, params)
        interviews = cursor.fetchall()

        interview_list = []
        for interview in interviews:
            interview_list.append({
                "id": interview[0],
                "user_id": interview[1],
                "date_of_interview": interview[2].isoformat(),
                "interview_questions": interview[3],
                "answers": interview[4],
                "created_at": interview[5].isoformat()
            })

        return jsonify({"status": "success", "interviews": interview_list}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# CREATE Interview
@app.route('/interviews', methods=['POST'])
def create_interview():
    try:
        data = request.json
        required_fields = ['user_id', 'date_of_interview', 'interview_questions', 'answers']
        
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO interview (
                user_id,
                date_of_interview,
                interview_questions,
                answers
            ) VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            data['user_id'],
            data['date_of_interview'],
            json.dumps(data['interview_questions']),
            json.dumps(data['answers'])
        ))

        interview_id = cursor.fetchone()[0]
        conn.commit()
        
        return jsonify({
            "status": "success",
            "interview_id": interview_id,
            "message": "Interview record created successfully"
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()



@app.route('/test', methods=['GET'])
def test():
    return "Hello, this is a test string!"


if __name__ == '__main__':
    print ("Hello, this is a test string!")
    app.run(port=5003, debug=True)
   
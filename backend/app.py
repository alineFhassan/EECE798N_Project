from flask import Flask, request, jsonify
import psycopg2
import os
import json
import requests
import numpy as np

HF_API_KEY = os.getenv('HUGGINGFACE_API_KEY')  # Get your free API key from https://huggingface.co/settings/tokens
HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"

def get_embedding(text):
    if not text.strip():
        return np.zeros(384).tolist()
    
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": text,
        "options": {"wait_for_model": True}
    }
    
    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json=payload,
            timeout=30  # Increased timeout for free tier
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"HF API Error: {response.status_code} - {response.text}")
            return np.zeros(384).tolist()
            
    except Exception as e:
        print(f"Embedding API failed: {str(e)}")
        return np.zeros(384).tolist()

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
        full_name = data.get('full_name')
        username = data.get('username')
        password = data.get('password')  # Remember to hash this before storing
        email = data.get('email')
        user_type = data.get('user_type')

        # Optionally, you can add validation here
        if not all([full_name, username, password, email, user_type]):
            return jsonify({"status": "error", "message": "All fields are required."}), 400

        # Hash the password (use a secure hashing method)
        # For example, using bcrypt:
        # hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (full_name, username, password, email, user_type)
            VALUES (%s, %s, %s, %s, %s);
        """, (full_name, username, password, email, user_type))  # Use hashed_password here

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

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, email, password, user_type FROM users 
            WHERE email = %s AND password = %s;
        """, (email, password))

        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            return jsonify({
                "status": "success",
                "user_id": user[0],
                "email": user[1],
                "user_type": user[3]
            }), 200
        else:
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
 
    

@app.route('/add_application', methods=['POST'])
def add_application():
    try:
        data = request.json
        cv_data = data.get('cv_data', {})

        # Generate combined text for embedding
        embedding_text = ""
        
        # 1. Skills
        embedding_text = ""

        # 1. Skills (Handle both strings and dictionaries)
        if 'skills' in cv_data:
            skills_list = []
            for skill in cv_data['skills']:
                if isinstance(skill, dict):
                    skills_list.append(skill.get('name', ''))  # Extract 'name' if dictionary
                else:
                    skills_list.append(str(skill))
            embedding_text += "Skills: " + ", ".join(skills_list) + "\n"

        # 2. Projects (Handle both strings and dictionaries)
        if 'projects' in cv_data:
            project_list = []
            for project in cv_data['projects']:
                if isinstance(project, dict):
                    # Concatenate all values if it's a dictionary
                    proj_str = " ".join([str(v) for v in project.values()])
                    project_list.append(proj_str)
                else:
                    project_list.append(str(project))
            embedding_text += "Projects: " + " | ".join(project_list) + "\n"

        # 3. Experience (Ensure all values are strings)
        for exp in cv_data.get('experience', []):
            exp_str = f"Role: {exp.get('role', '')} at {exp.get('company', '')}. "
            exp_str += " ".join([str(resp) for resp in exp.get('responsibilities', [])])
            embedding_text += exp_str + "\n"

        # 4. Education (Handle GPA formatting)
        for edu in cv_data.get('education', []):
            edu_str = f"Education: {edu.get('degree', '')} from {edu.get('school', '')}"
            if 'gpa' in edu and edu['gpa']:
                edu_str += f" (GPA: {edu['gpa']})"
            embedding_text += edu_str + "\n"

        # 5. Certifications (Handle empty issuers)
        for cert in cv_data.get('certifications', []):
            issuer = cert.get('issuer', 'Unknown')
            cert_str = f"Certification: {cert.get('name', '')}"
            if issuer:
                cert_str += f" by {issuer}"
            embedding_text += cert_str + "\n"

        # Generate embedding
        embedding = get_embedding(embedding_text)


        gender = cv_data.get('gender', 'Not Specified')
        if isinstance(gender, list):
            gender = ", ".join(gender)  # Converts ["male"] → "male"

        # Ensure phone_number is string
        phone_number = str(cv_data.get('phone_number', '000-000-0000'))[:15]
        
        # Extract other fields
        name = cv_data.get('name', 'Default Name')
        email = cv_data.get('email', 'default@example.com')
        phone_number = cv_data.get('phone_number', '000-000-0000')
        achievements = json.dumps(cv_data.get('certifications', []))
        skills = json.dumps(cv_data.get('skills', []))
        experience = json.dumps(cv_data.get('experience', []))
        exp_years = sum(
            exp.get('years', 0) 
            for exp in cv_data.get('experience', []) 
            if isinstance(exp.get('years', 0), (int, float))
        )
        education = json.dumps(cv_data.get('education', []))
        address = json.dumps(cv_data.get('address', {}))
        date_of_birth = cv_data.get('date_of_birth', '1970-01-01')
        gender = cv_data.get('gender', 'Undefined')
        user_id = data.get('user_id')

        # Database insertion
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO application (
                name, email, phone_number, achievements,
                skills, experience, exp_years, education,
                address, date_of_birth, gender, user_id, embedding
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            name, email, phone_number, achievements,
            skills, experience, exp_years, education,
            address, date_of_birth, gender, user_id,
            json.dumps(embedding)  # Serialize embedding array
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "Application added successfully."}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/get_applications', methods=['GET'])
def get_applications():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM application;")
        applications = cursor.fetchall()

        # Convert to a list of dictionaries
        application_list = []
        for application in applications:
            application_list.append({
                "user_id": application[13],  
                "id": application[0],                # Adjust based on your table structure
                "name": application[1],
                "email": application[2],
                "phone_number": application[3],
                "achievements": application[4],
                "skills": application[5],
                "experience": application[6],
                "exp_years": application[7],
                "education": application[8],
                "address": application[9],
                "date_of_birth": application[10],
                "gender": application[11],
                "embedding": application[12],
                         # Assuming you added user_id
            })

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "applications": application_list}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/applications/<int:application_id>', methods=['GET'])
def get_application(application_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM application 
            WHERE id = %s;
        """, (application_id,))

        application = cursor.fetchone()
        
        if not application:
            return jsonify({"status": "error", "message": "Application not found"}), 404

        application_data = {
            "user_id": application[13],
            "id": application[0],
            "name": application[1],
            "email": application[2],
            "phone_number": application[3],
            "achievements": application[4],
            "skills": application[5],
            "experience": application[6],
            "exp_years": application[7],
            "education": application[8],
            "address": application[9],
            "date_of_birth": application[10].isoformat() if application[10] else None,
            "gender": application[11],
            "embedding": application[12]
        }

        return jsonify({
            "status": "success",
            "application": application_data
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
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
   
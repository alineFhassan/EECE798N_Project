from flask import Flask, request, jsonify
import psycopg2
import os
import json

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

@app.route('/check_db', methods=['GET'])
def check_db():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "success", "message": "Database connection successful!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/users', methods=['GET'])
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

        # Extract fields from cv_data
        name = cv_data.get('name', 'Default Name')  # You can set a default name or adjust accordingly
        email = cv_data.get('email', 'default@example.com')  # Set a default email if needed
        phone_number = cv_data.get('phone_number', '000-000-0000')  # Default phone number
        achievements = json.dumps(cv_data.get('certifications', []))  # Convert certifications to JSON
        skills = json.dumps(cv_data.get('skills', []))  # Convert skills to JSON
        experience = json.dumps(cv_data.get('experience', []))  # Convert experience to JSON
        exp_years = sum(exp.get('years', 0) for exp in cv_data.get('experience', []) if isinstance(exp.get('years', 0), (int, float)))  # Calculate total experience years
        education = json.dumps(cv_data.get('education', []))  # Convert education to JSON
        address = json.dumps(cv_data.get('address', {}))  # Assuming address is included in cv_data
        date_of_birth = cv_data.get('date_of_birth', '1970-01-01')  # Default date of birth
        gender = cv_data.get('gender', 'Not Specified')  # Default gender
        user_id = data.get('user_id')  # Include user_id from the main request

        # Validate required fields
        #if not all([name, email, phone_number, achievements, skills, experience, exp_years, education, date_of_birth, gender, user_id]):
         #   return jsonify({"status": "error", "message": "All fields are required."}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO application (
                name,
                email,
                phone_number,
                achievements,
                skills,
                experience,
                exp_years,
                education,
                address,
                date_of_birth,
                gender,
                user_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (name, email, phone_number, achievements, skills, experience, exp_years, education, address, date_of_birth, gender, user_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "Application added successfully."}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
    
@app.route('/applications', methods=['GET'])
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

@app.route('/test', methods=['GET'])
def test():
    return "Hello, this is a test string!"


if __name__ == '__main__':
    print ("Hello, this is a test string!")
    app.run(port=5003, debug=True)
   
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

@app.route('/check_db', methods=['GET'])
def check_db():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "success", "message": "Database connection successful!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/applicant', methods=['POST'])
def add_applicant():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        achievements = json.dumps(data.get('achievements'))  # Convert to JSON
        skills = json.dumps(data.get('skills'))              # Convert to JSON
        experience = json.dumps(data.get('experience'))      # Convert to JSON
        education = json.dumps(data.get('education'))        # Convert to JSON
        embedding = data.get('embedding')                     # Keep as is, assuming it's a list

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO applicant (name, email, phone_number, achievements, skills, experience, education, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (name, email, phone_number, achievements, skills, experience, education, embedding))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "Applicant added."}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/test', methods=['GET'])
def test():
    return "Hello, this is a test string!"


if __name__ == '__main__':
    print ("Hello, this is a test string!")
    app.run(port=5003, debug=True)
   
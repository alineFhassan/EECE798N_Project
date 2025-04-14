from flask import Flask, request, jsonify
import requests
from mistralai import Mistral

app = Flask(__name__)

# Configuration
MISTRAL_API_KEY = ""
DATABASE_API_URL = "http://localhost:5001/save-cv" 
mistral_client = Mistral(api_key=MISTRAL_API_KEY)
MODEL_NAME = "ft:open-mistral-7b:c099368a:20250414:4d9d311e"

def fetch_cv_data(candidate_id):
    """Get CV data from database"""
    try:
        response = requests.get(
            f"{DATABASE_API_URL}/cvs/{candidate_id}",
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch CV: {str(e)}")

def fetch_job_data(job_id):
    """Get job data from database"""
    try:
        response = requests.get(
            f"{DATABASE_API_URL}/jobs/{job_id}",
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch job: {str(e)}")

def save_questions(questions, candidate_id, job_id):
    """Save generated questions to database"""
    try:
        payload = {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "questions": questions
        }
        response = requests.post(
            f"{DATABASE_API_URL}/interview-questions",
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to save questions: {str(e)}")

def generate_interview_questions(cv_data, job_data):
    """Generate questions using Mistral"""
    prompt = f"""
    You are an expert recruitment AI assistant tasked with generating interview questions tailored to a specific candidate's profile and job posting.Given the following JSON representation of CV:
    
    Candidate CV:
    {{
        "education": {cv_data.get('education', [])},
        "experience": {cv_data.get('experience', [])},
        "skills": {cv_data.get('skills', [])},
        "achievements": {cv_data.get('achievements', [])}
    }}
    
    and Job Posting:
    {{
        "title": "{job_data.get('job_title', '')}",
        "requirements": {job_data.get('requirements', [])},
        "responsibilities": {job_data.get('responsibilities', [])},
        "experience_needed": "{job_data.get('experience', '')}"
    }}
    
   Based on the given candidate information encoded in the JSON above, create a structured response in JSON format. Here is the structure of the JSON:{{  \"general\": [\"2-3 questions about the candidate's background, motivation, and role interest.\"],  \"technical\": [\"4-5 questions focusing on the candidate's specific skills and job requirements.\"],  \"behavioral\": [\"2-3 questions to evaluate teamwork, problem-solving, and situational responses.\"].Each object should independently follow the structure above, and ensure the total number of interview questions across all categories does not exceed 10. Ensure each category (`general`, `technical`, `behavioral`) contains at least one question where applicable.Focus on tailoring the questions specifically to the candidate's CV and the job posting.Use professional and conversational language aligned with real-world interview scenarios. Ensure only to return the format mentioned above and nothing else."}}
    """
    
    response = mistral_client.chat.complete(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        raise Exception("Failed to parse questions from AI response")

@app.route('/generate-questions', methods=['POST'])
def handle_question_generation():
    try:
        # Validate input
        data = request.json
        required_fields = ['candidate_id', 'job_id']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing candidate_id or job_id"}), 400

        # Step 1: Fetch data from database
        cv_data = fetch_cv_data(data['candidate_id'])
        job_data = fetch_job_data(data['job_id'])
        
        # Step 2: Generate questions
        questions = generate_interview_questions(cv_data, job_data)
        
        # Step 3: Save to database
        save_response = save_questions(questions, data['candidate_id'], data['job_id'])
        
        return jsonify({
            "status": "success",
            "questions": questions,
            "database_response": save_response
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5002, debug=True)  # Running on different port
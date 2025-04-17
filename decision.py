from flask import Flask, request, jsonify
import requests
import numpy as np
from datetime import datetime

app = Flask(__name__)

# Configuration
HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
HF_TOKEN = "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"

# Thresholds
THRESHOLDS = {
    "skills_vs_requirements": 0.6,
    "education_vs_title": 0.5,
    "responsibilities_vs_skills": 0.55,
    "responsibilities_vs_experience": 0.5,
    "experience_years": 0.8,
    "title_vs_experience": 0.5,
    "overall_interview": 0.5
}

def get_embeddings(texts: list) -> list:
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(
        HF_API_URL,
        headers=headers,
        json={"inputs": texts, "options": {"wait_for_model": True}}
    )
    response.raise_for_status()
    return response.json()

def cosine_similarity(a: list, b: list) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def years_experience_match(candidate_years: int, required_years: int) -> float:
    return min(candidate_years / required_years, 1.0) if required_years > 0 else 1.0

def evaluate_cv_vs_job(cv_data: dict, job_data: dict) -> dict:
    texts = (
        cv_data["skills"] + 
        [cv_data["education"]] + 
        cv_data["responsibilities"] + 
        [job_data["title"]] + 
        job_data["requirements"] + 
        job_data["responsibilities"]
    )
    embeddings = get_embeddings(texts)
    
    split_points = [
        len(cv_data["skills"]),
        len(cv_data["skills"]) + 1,
        len(cv_data["skills"]) + 1 + len(cv_data["responsibilities"])
    ]
    
    cv_skills = embeddings[:split_points[0]]
    cv_education = embeddings[split_points[0]:split_points[1]]
    cv_responsibilities = embeddings[split_points[1]:split_points[2]]
    job_title = embeddings[split_points[2]]
    job_reqs = embeddings[split_points[2]+1:split_points[2]+1+len(job_data["requirements"])]
    job_resps = embeddings[split_points[2]+1+len(job_data["requirements"]):]

    scores = {
        "skills_vs_requirements": max(
            [cosine_similarity(skill, req) for skill in cv_skills for req in job_reqs],
            default=0
        ),
        "education_vs_title": cosine_similarity(cv_education[0], job_title),
        "responsibilities_vs_skills": max(
            [cosine_similarity(resp, skill) for resp in cv_responsibilities for skill in cv_skills],
            default=0
        ),
        "responsibilities_vs_experience": max(
            [cosine_similarity(resp, job_resp) for resp in cv_responsibilities for job_resp in job_resps],
            default=0
        ),
        "experience_years": years_experience_match(
            cv_data.get("years_experience", 0),
            job_data.get("required_experience_years", 0)
        ),
        "title_vs_experience": cosine_similarity(
            job_title,
            get_embeddings([f"{cv_data.get('years_experience', 0)} years experience"])[0]
        )
    }

    meets_threshold = {k: v >= THRESHOLDS[k] for k, v in scores.items()}
    met_count = sum(meets_threshold.values())
    total_metrics = len(THRESHOLDS)
    percentage_met = (met_count / total_metrics) * 100
    
    qualified = percentage_met >= 70
    reason = "Qualified" if qualified else f"Only {percentage_met:.1f}% of metrics met threshold (needed 70%)"

    return {
        "scores": scores,
        "meets_threshold": meets_threshold,
        "metrics_met": f"{met_count}/{total_metrics}",
        "percentage_met": f"{percentage_met:.1f}%",
        "qualified": qualified,
        "reason": reason,
        "thresholds": THRESHOLDS.copy()
    }

@app.route('/final-decision', methods=['POST'])
def handle_evaluation():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['cv_data', 'job_data']
        if not all(field in data for field in required_fields):
            return jsonify({
                "status": "error",
                "message": "Missing required fields",
                "timestamp": datetime.now().isoformat()
            }), 400

        # Perform CV vs Job evaluation
        evaluation = evaluate_cv_vs_job(data['cv_data'], data['job_data'])
        
        # Convert boolean values to strings for JSON serialization
        evaluation['meets_threshold'] = {k: str(v) for k, v in evaluation['meets_threshold'].items()}
        evaluation['qualified'] = str(evaluation['qualified'])
        
        # Process interview evaluation if provided
        if 'interview_evaluation' in data:
            interview_scores = data['interview_evaluation'].get('overall_scores', {})
            
            if all(k in interview_scores for k in ['requirements', 'responsibilities']):
                req_pass = interview_scores['requirements'] >= THRESHOLDS['overall_interview']
                resp_pass = interview_scores['responsibilities'] >= THRESHOLDS['overall_interview']
                
                evaluation['interview_results'] = {
                    'requirements': {
                        'score': interview_scores['requirements'],
                        'passed': str(req_pass),  # Convert to string
                        'threshold': THRESHOLDS['overall_interview']
                    },
                    'responsibilities': {
                        'score': interview_scores['responsibilities'],
                        'passed': str(resp_pass),  # Convert to string
                        'threshold': THRESHOLDS['overall_interview']
                    },
                    'interview_qualified': str(req_pass and resp_pass),  # Convert to string
                    'interview_reason': (
                        "Passed both interview components" if (req_pass and resp_pass) else
                        "Failed interview: " + 
                        ("requirements" if not req_pass else "") + 
                        (" and " if not req_pass and not resp_pass else "") +
                        ("responsibilities" if not resp_pass else "")
                    )
                }
                
                # Final qualification
                fully_qualified = evaluation['qualified'] == 'True' and (req_pass and resp_pass)
                evaluation['fully_qualified'] = str(fully_qualified)  # Convert to string
                evaluation['final_reason'] = (
                    "Fully qualified - passed all criteria" if fully_qualified else
                    f"Disqualified - {evaluation['reason']}" if evaluation['qualified'] == 'False' else
                    f"Disqualified - {evaluation['interview_results']['interview_reason']}"
                )
            else:
                evaluation['interview_warning'] = "Missing required interview scores"

        return jsonify({
            "status": "success",
            "evaluation": evaluation,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006)
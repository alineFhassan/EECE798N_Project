from flask import Flask, request, jsonify
import requests
import numpy as np
from typing import List, Dict

app = Flask(__name__)

HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
HF_TOKEN = "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"  # Secure this in production
COVERAGE_THRESHOLD = 0.5  # Minimum similarity to consider "covered"

# --- UTILS ---

def get_embeddings(texts: List[str]) -> List[List[float]]:
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(
        HF_API_URL,
        headers=headers,
        json={"inputs": texts, "options": {"wait_for_model": True}}
    )
    response.raise_for_status()
    return response.json()

def cosine_similarity(a: List[float], b: List[float]) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def combine_questions_and_answers(questions: Dict[str, List[str]], answers: Dict[str, List[str]]) -> List[str]:
    combined = []
    for category in answers:
        q_list = questions.get(category, [])
        a_list = answers[category]
        for i, answer in enumerate(a_list):
            question = q_list[i] if i < len(q_list) else ""
            combined.append(f"{question.strip()} {answer.strip()}" if question else answer.strip())
    return combined

# --- EVALUATION ---

def evaluate_against_job(combined_texts: List[str], job: Dict) -> Dict:
    requirements = job["requirements"]
    responsibilities = job["responsibilities"]
    all_texts = combined_texts + requirements + responsibilities
    embeddings = get_embeddings(all_texts)

    answer_embeddings = embeddings[:len(combined_texts)]
    req_embeddings = embeddings[len(combined_texts):len(combined_texts) + len(requirements)]
    resp_embeddings = embeddings[len(combined_texts) + len(requirements):]

    result = {
        "title": job.get("title", "Untitled Job"),
        "answer_analysis": [],
        "requirements_coverage": [],
        "responsibilities_coverage": [],
        "overall_scores": {"requirements": {}, "responsibilities": {}, "combined": 0.0}
    }

    req_scores = []
    resp_scores = []

    # For calculating average over all answers
    req_all_scores = []
    resp_all_scores = []

    for i, emb in enumerate(answer_embeddings):
        req_sim = [cosine_similarity(emb, r) for r in req_embeddings]
        best_req_score = max(req_sim) if req_sim else 0
        best_req_idx = req_sim.index(best_req_score) if best_req_score > 0 else -1
        best_req = requirements[best_req_idx] if best_req_idx >= 0 else None
        req_all_scores.append(best_req_score)

        resp_sim = [cosine_similarity(emb, r) for r in resp_embeddings]
        best_resp_score = max(resp_sim) if resp_sim else 0
        best_resp_idx = resp_sim.index(best_resp_score) if best_resp_score > 0 else -1
        best_resp = responsibilities[best_resp_idx] if best_resp_idx >= 0 else None
        resp_all_scores.append(best_resp_score)

        result["answer_analysis"].append({
            "answer_index": i,
            "best_requirement_match": best_req,
            "requirement_score": best_req_score,
            "best_responsibility_match": best_resp,
            "responsibility_score": best_resp_score
        })

        if best_req_score >= COVERAGE_THRESHOLD:
            req_scores.append(best_req_score)
            result["requirements_coverage"].append({
                "requirement": best_req,
                "answer_index": i,
                "score": best_req_score
            })

        if best_resp_score >= COVERAGE_THRESHOLD:
            resp_scores.append(best_resp_score)
            result["responsibilities_coverage"].append({
                "responsibility": best_resp,
                "answer_index": i,
                "score": best_resp_score
            })

    # Scoring logic: all vs matched-only
    result["overall_scores"]["requirements"] = {
        "average_score_all_answers": round(sum(req_all_scores) / len(req_all_scores), 3) if req_all_scores else 0,
        "average_score_matched_only": round(sum(req_scores) / len(req_scores), 3) if req_scores else 0,
        "coverage_percentage": f"{round(100 * len(req_scores) / len(answer_embeddings), 1)}%" if answer_embeddings else "0%"
    }

    result["overall_scores"]["responsibilities"] = {
        "average_score_all_answers": round(sum(resp_all_scores) / len(resp_all_scores), 3) if resp_all_scores else 0,
        "average_score_matched_only": round(sum(resp_scores) / len(resp_scores), 3) if resp_scores else 0,
        "coverage_percentage": f"{round(100 * len(resp_scores) / len(answer_embeddings), 1)}%" if answer_embeddings else "0%"
    }

    result["overall_scores"]["combined"] = round((
        result["overall_scores"]["requirements"]["average_score_all_answers"] +
        result["overall_scores"]["responsibilities"]["average_score_all_answers"]
    ) / 2, 3)

    return result

# --- FLASK ROUTE ---

@app.route('/evaluate-multi-job', methods=['POST'])
def evaluate_multiple_jobs():
    try:
        data = request.json
        required_fields = ['interview_questions', 'interview_answers', 'jobs']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        combined_texts = combine_questions_and_answers(data["interview_questions"], data["interview_answers"])
        job_results = []

        for job in data["jobs"]:
            if "requirements" in job and "responsibilities" in job:
                job_eval = evaluate_against_job(combined_texts, job)
                job_results.append(job_eval)

        # Find best matching job by combined score
        best_job = max(job_results, key=lambda j: j["overall_scores"]["combined"], default=None)

        return jsonify({
            "status": "success",
            "best_match": best_job
        })

    except requests.exceptions.HTTPError as e:
        return jsonify({
            "error": "Hugging Face API error",
            "details": str(e),
            "response": e.response.text if e.response else None
        }), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ENTRY POINT ---

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)

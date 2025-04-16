from flask import Flask, request, jsonify
import requests
import numpy as np
from typing import List, Dict

app = Flask(__name__)

# Configuration - Replace with your actual Hugging Face token
HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
HF_TOKEN = "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"  # Secure this token in production

# Similarity threshold for considering a requirement/responsibility "covered"
COVERAGE_THRESHOLD = 0.5  # Adjust this value based on your needs

# --- UTILS ---

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Fetch embeddings from Hugging Face API."""
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(
        HF_API_URL,
        headers=headers,
        json={"inputs": texts, "options": {"wait_for_model": True}}
    )
    response.raise_for_status()
    return response.json()

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def combine_questions_and_answers(questions: Dict[str, List[str]], answers: Dict[str, List[str]]) -> List[str]:
    """Combine questions and answers into full text blocks."""
    combined_texts = []
    for category in answers:
        q_list = questions.get(category, [])
        a_list = answers[category]
        for i, answer in enumerate(a_list):
            question = q_list[i] if i < len(q_list) else ""
            combined_text = f"{question.strip()} {answer.strip()}" if question else answer.strip()
            combined_texts.append(combined_text)
    return combined_texts

# --- CORE LOGIC ---

def evaluate_answers(
    combined_texts: List[str],
    requirements: List[str],
    responsibilities: List[str]
) -> Dict:
    """Evaluate answers against requirements and responsibilities."""
    all_texts = combined_texts + requirements + responsibilities
    embeddings = get_embeddings(all_texts)

    answer_embeddings = embeddings[:len(combined_texts)]
    req_embeddings = embeddings[len(combined_texts):len(combined_texts)+len(requirements)]
    resp_embeddings = embeddings[len(combined_texts)+len(requirements):]

    results = {
        "answer_analysis": [],
        "requirements_coverage": [],
        "responsibilities_coverage": [],
        "overall_scores": {
            "requirements": 0.0,  # Average of ALL requirement matches above threshold
            "responsibilities": 0.0  # Average of ALL responsibility matches above threshold
        }
    }

    req_scores = []
    resp_scores = []

    for i, embedding in enumerate(answer_embeddings):
        # Requirement comparison
        req_scores_batch = [cosine_similarity(embedding, req) for req in req_embeddings]
        best_req_score = max(req_scores_batch) if req_scores_batch else 0
        best_req_idx = req_scores_batch.index(best_req_score) if best_req_score > 0 else -1
        best_req = requirements[best_req_idx] if best_req_idx >= 0 else None

        # Responsibility comparison
        resp_scores_batch = [cosine_similarity(embedding, resp) for resp in resp_embeddings]
        best_resp_score = max(resp_scores_batch) if resp_scores_batch else 0
        best_resp_idx = resp_scores_batch.index(best_resp_score) if best_resp_score > 0 else -1
        best_resp = responsibilities[best_resp_idx] if best_resp_idx >= 0 else None

        # Record analysis
        results["answer_analysis"].append({
            "answer_index": i,
            "best_requirement_match": best_req,
            "requirement_score": best_req_score,
            "best_responsibility_match": best_resp,
            "responsibility_score": best_resp_score
        })

        # Track scores for overall averages
        if best_req_score >= COVERAGE_THRESHOLD:
            results["requirements_coverage"].append({
                "requirement": best_req,
                "answer_index": i,
                "score": best_req_score,
                "supporting_answer": combined_texts[i]
            })
            req_scores.append(best_req_score)

        if best_resp_score >= COVERAGE_THRESHOLD:
            results["responsibilities_coverage"].append({
                "responsibility": best_resp,
                "answer_index": i,
                "score": best_resp_score,
                "supporting_answer": combined_texts[i]
            })
            resp_scores.append(best_resp_score)

    # Calculate overall averages
    results["overall_scores"]["requirements"] = sum(req_scores)/len(req_scores) if req_scores else 0
    results["overall_scores"]["responsibilities"] = sum(resp_scores)/len(resp_scores) if resp_scores else 0

    return results

# --- ROUTES ---

@app.route('/evaluate', methods=['POST'])
def handle_evaluation():
    try:
        data = request.json

        required_fields = ['interview_questions', 'interview_answers', 'requirements', 'responsibilities']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing one or more required fields"}), 400

        combined_texts = combine_questions_and_answers(
            questions=data["interview_questions"],
            answers=data["interview_answers"]
        )

        evaluation = evaluate_answers(
            combined_texts=combined_texts,
            requirements=data["requirements"],
            responsibilities=data["responsibilities"]
        )

        return jsonify({
            "status": "success",
            "evaluation": evaluation
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
    app.run(host='0.0.0.0', port=5004)
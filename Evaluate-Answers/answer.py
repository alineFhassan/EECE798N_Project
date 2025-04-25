from flask import Flask, request, jsonify
import requests
import numpy as np
from typing import List
import os
app = Flask(__name__)

HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
HF_TOKEN = os.getenv("HF_TOKEN")    # Secure this token in production

def get_embeddings(texts: List[str]) -> List[List[float]]:
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(
        HF_API_URL,
        headers=headers,
        json={"inputs": texts, "options": {"wait_for_model": True}}
    )
    response.raise_for_status()
    return response.json()

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def evaluate_answers_only(
    answers: List[str],
    requirements: List[str],
    responsibilities: List[str]
) -> dict:
    all_texts = answers + requirements + responsibilities
    embeddings = get_embeddings(all_texts)

    num_answers = len(answers)
    num_reqs = len(requirements)
    num_resps = len(responsibilities)

    answer_embeddings = np.array(embeddings[:num_answers])
    req_embeddings = np.array(embeddings[num_answers:num_answers + num_reqs])
    resp_embeddings = np.array(embeddings[num_answers + num_reqs:])

    # Normalize embeddings
    def normalize(x): return x / np.linalg.norm(x, axis=1, keepdims=True)
    answer_embeddings = normalize(answer_embeddings)
    req_embeddings = normalize(req_embeddings)
    resp_embeddings = normalize(resp_embeddings)

    # Cosine similarity matrices
    req_sim_matrix = np.matmul(answer_embeddings, req_embeddings.T)
    resp_sim_matrix = np.matmul(answer_embeddings, resp_embeddings.T)

    # Best match score for each answer
    req_best_scores = np.max(req_sim_matrix, axis=1)
    resp_best_scores = np.max(resp_sim_matrix, axis=1)

    # Average best scores
    req_avg = float(np.mean(req_best_scores))
    resp_avg = float(np.mean(resp_best_scores))

    return {
        "requirements": {
            "average_score_all_answers": round(req_avg, 4)
        },
        "responsibilities": {
            "average_score_all_answers": round(resp_avg, 4)
        }
    }

@app.route('/evaluate', methods=['POST'])
def handle_evaluation():
    try:
        data = request.json
        summary_only = request.args.get('summary', 'false').lower() == 'true'

        evaluation = evaluate_answers_only(
            answers=[a for sublist in data["interview_answers"].values() for a in sublist],
            requirements=data["requirements"],
            responsibilities=data["responsibilities"]
        )

        # Always include "overall_scores" in the response for consistency
        response = {
            "status": "success",
            "evaluation": {
                "overall_scores": evaluation
            }
        }
        print("res", response, flush=True)
        # If summary_only is False, include the full evaluation
        if not summary_only:
            response["evaluation"].update(evaluation)

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3005, debug=True)

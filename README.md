# EECE798N_Project

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Technologies Used](#technologies-used)
- [Setup and Installation](#setup-and-installation)
- [Running the Application](#running-the-application)


---

## Overview
The **EECE798N_Project** is a comprehensive job application management system designed to streamline the hiring process for employers and job seekers. It includes features such as job posting, CV extraction, job matching, interview scheduling, and answer evaluation.

---

## Features
- **Job Posting**: Employers can post job openings with detailed requirements and responsibilities.
- **CV Extraction**: Extract and format CVs using AI-powered tools.
- **Job Matching**: Match CVs to job descriptions based on skills and experience.
- **Interview Scheduling**: Schedule and manage interviews with a built-in calendar.
- **Answer Evaluation**: Evaluate interview answers using AI-based scoring.
- **Dashboard**: Interactive dashboards for HR and job seekers to track progress and manage tasks.

---

## Project Structure
The project is organized into multiple services, each with its own functionality:
EECE798N_Project ├── backend/ # Backend service for core logic ├── cv-job-matching/ # Service for matching CVs to job descriptions ├── CV-Format/ # Service for CV extraction and formatting ├── frontend/ # Frontend service for user interaction ├── Interview-Questions/ # Service for generating interview questions ├── Evaluate-Answers/ # Service for evaluating interview answers ├── job-description/ # Service for generating job descriptions ├── mysql/ # MySQL database schema and initialization ├── docker-compose.yml # Docker Compose configuration ├── k8s/ # Kubernetes deployment files └── README.md # Project documentation

---

## Technologies Used
- **Frontend**: Flask, HTML, CSS, JavaScript
- **Backend**: Flask, Python
- **Database**: MySQL
- **AI Services**: OpenAI, Hugging Face, Mistral
- **Containerization**: Docker, Docker Compose
- **Orchestration**: Kubernetes
- **Monitoring**: Prometheus, Grafana

---

## Setup and Installation

### Prerequisites
- Docker and Docker Compose installed
- Python 3.8 or higher
- MySQL installed locally or accessible remotely
- Kubernetes cluster (optional for deployment)

### Installation Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/alineFhassan/EECE798N_Project.git
   cd EECE798N_Project
2. Create a .env file in the root directory and add the required environment variables.
   ```
   # API Keys
   OPENAI_API_KEY=your_openai_api_key
   HF_TOKEN=your_huggingface_api_token
   MISTRAL_API_KEY=your_mistral_api_key

   ```
3. Build and start the services using Docker Compose:
docker-compose --env-file \your-path\EECE798N_Project-1\.github\.env up --build

4. Access the application:

- Frontend: http://localhost:3000
- Backend: http://localhost:5000

## Running the application
### As an Applicant
1. As an applicant, start first by signing up and giving the right information. Then login using the registered credentials.

2. Upload the cv in the Upload PDF page. (Note: You can't apply to any job before applying the cv)

3. You can now apply to the offered jobs available in the jobseeker dashboard.

4. Pay attention to your email, as decisions are sent by email.

### As a department
1. Login using your credentials. For demo purposes, below are some departments that are available to login into:

| Department               | Email                     | Password |
|--------------------------|---------------------------|----------|
| AI                      | ai@gmail.com              | ai       |
| Finance                 | finance@gmail.com         | finance  |
| IT                      | it@gmail.com              | it       |
| Marketing               | marketing@gmail.com       | marketing|
| Software Engineering    | soft_eng@gmail.com        | soft     |

2. You can view all offered jobs in your department (if any) and then you can view the applicants.

3. To add new job posting, add the necessary information and automatically the job offering will be generated.

### As an HR
1. Login using the credentials: hr@gmail.com ; password: hr

2. You can view all the offered jobs and the status of the applicants. 

3. If the applicant was disqualified, you can click to send him a regret email. If he/she was qualified, then you can schedule an HR interview.

4. To schedule an interview, you will have to enter the meeting information to be sent to the applicant. If there is a time conflict, you will be notified.

5. The answers of the interview are generated automatically to be used by the HR for conducting the interview.

6. After/during the interview, the HR can go and fill the applicant's answers, who will either be qualified or disqualified based on the answers and will receive emails anyway.
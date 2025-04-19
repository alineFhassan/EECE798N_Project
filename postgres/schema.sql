-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table (combines both user types)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,  -- Store hashed passwords
    date_of_birth DATE NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    user_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Departments table (for companies/departments)
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,  -- Store hashed passwords
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Applicant CV table with embeddings
CREATE TABLE applicant_cv (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    education JSONB,
    skills JSONB,
    experience JSONB,
    experience_years INTEGER,
    projects JSONB,
    certifications JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Jobs table with embeddings
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    job_level VARCHAR(100) NOT NULL,
    years_experience VARCHAR(50) NOT NULL,
    requirements JSONB NOT NULL,
    responsibilities JSONB NOT NULL,
    required_certifications JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    date_offered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Applied jobs table
CREATE TABLE applied_jobs (
    id SERIAL PRIMARY KEY,
    applicant_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    scores JSONB,
    thresholds JSONB,
    meets_threshold JSONB,
    passed_criteria VARCHAR(10),
    qualified_cv BOOLEAN,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (applicant_id, job_id)
);

-- Interviews table
CREATE TABLE interviews (
    id SERIAL PRIMARY KEY,
    applicant_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    meeting_title VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    questions JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (applicant_id, job_id, date, start_time)
);

-- Interview answers table
CREATE TABLE interview_answers (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    answers JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Answer evaluations table
CREATE TABLE answer_evaluations (
    id SERIAL PRIMARY KEY,
    answer_id INTEGER NOT NULL REFERENCES interview_answers(id) ON DELETE CASCADE,
    avg_score_requirements FLOAT,
    avg_score_responsibilities FLOAT,
    full_evaluation TEXT,
    qualified_interview BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Technical interviews table
CREATE TABLE technical_interviews (
    id SERIAL PRIMARY KEY,
    applicant_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    interview_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Best matches table
CREATE TABLE best_matches (
    id SERIAL PRIMARY KEY,
    applicant_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    evaluation JSONB,
    match_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pending decisions table
CREATE TABLE pending_decisions (
    id SERIAL PRIMARY KEY,
    applicant_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (applicant_id, job_id)
);
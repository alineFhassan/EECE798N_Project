-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;


CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,  -- Ensure to hash passwords
    email VARCHAR(255) UNIQUE NOT NULL,
    user_type VARCHAR(50) NOT NULL,   -- e.g., 'applicant', 'recruiter', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create sample table
CREATE TABLE application (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone_number VARCHAR(20),  -- New field for phone number
    achievements JSONB,        -- Stores list of achievements/accomplishments
    skills JSONB,              -- Stores technical/professional skills
    experience JSONB,          -- Stores work experience history
    exp_years VARCHAR(50),
    education JSONB,           -- Stores educational background
    address JSONB,             -- Stores address details
    date_of_birth DATE,        -- Stores date of birth
    gender VARCHAR(10),        -- Stores gender
    embedding vector(384)      -- OpenAI embedding vector
);

ALTER TABLE application ADD COLUMN user_id INT;

ALTER TABLE application 
ADD CONSTRAINT fk_user 
FOREIGN KEY (user_id) 
REFERENCES users(id);

DROP TABLE IF EXISTS jobs;

-- Then create new table with proper schema
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    position VARCHAR(255),
    long_description TEXT,
    english_level VARCHAR(50),
    required_skills JSONB, 
    exp_years VARCHAR(50),
    embedding vector(384)  
);
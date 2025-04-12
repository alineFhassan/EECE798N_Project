-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create sample table
CREATE TABLE applicant (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone_number VARCHAR(20),  -- New field for phone number
    achievements JSONB,        -- Stores list of achievements/accomplishments
    skills JSONB,              -- Stores technical/professional skills
    experience JSONB,          -- Stores work experience history
    education JSONB,           -- Stores educational background
    address JSONB,             -- Stores address details
    date_of_birth DATE,        -- Stores date of birth
    gender VARCHAR(10),        -- Stores gender
    embedding vector(384)      -- OpenAI embedding vector
);


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
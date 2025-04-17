CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE Users (
    userID UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password VARCHAR(255),
    name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'student',
    phone VARCHAR(20),
    address TEXT,
    age INTEGER,
    date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Applications (
    applicationID UUID PRIMARY KEY DEFAULT uuid_generate_v4(), -- Add default UUID generation
    userID UUID REFERENCES Users(userID),
    program VARCHAR(255),
    education_level VARCHAR(100),
    previous_institution VARCHAR(255),
    gpa NUMERIC(3, 2),
    personal_statement TEXT,
    prerequisites_completed BOOLEAN,
    status VARCHAR(50) DEFAULT 'submitted',
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Documents (
    documentID UUID PRIMARY KEY,
    applicationID UUID REFERENCES Applications(applicationID),
    document_name VARCHAR(255),
    document_type VARCHAR(50),
    file_path VARCHAR(255),
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Interviews (
    interviewID UUID PRIMARY KEY,
    applicationID UUID REFERENCES Applications(applicationID),
    officerID UUID REFERENCES Users(userID),
    schedule_date TIMESTAMP,
    location VARCHAR(255),
    notes TEXT,
    status VARCHAR(50) DEFAULT 'scheduled' -- 'scheduled', 'completed', 'cancelled'
);

CREATE TABLE Feedback (
    feedbackID UUID PRIMARY KEY,
    applicationID UUID REFERENCES Applications(applicationID),
    officerID UUID REFERENCES Users(userID),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

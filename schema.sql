CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE Users (
    userID UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password VARCHAR(255),
    name VARCHAR(255),
    age INT,
);

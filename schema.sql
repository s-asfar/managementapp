CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE Users (
    userID UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password VARCHAR(255),
    name VARCHAR(255),
    age INT,
    height VARCHAR(10),
    weight INT,
    goal VARCHAR(50)
);

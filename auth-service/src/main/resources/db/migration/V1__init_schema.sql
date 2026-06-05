-- V1: Initial schema — users and api_keys tables

CREATE TABLE IF NOT EXISTS users (
    id            VARCHAR(32)  PRIMARY KEY,
    username      VARCHAR(64)  NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    status        VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE',
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users (username);
CREATE INDEX idx_users_email    ON users (email);

CREATE TABLE IF NOT EXISTS api_keys (
    id            VARCHAR(32)  PRIMARY KEY,
    user_id       VARCHAR(32)  NOT NULL REFERENCES users(id),
    key_hash      VARCHAR(255) NOT NULL,
    name          VARCHAR(128),
    revoked       BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    last_used_at  TIMESTAMP
);

CREATE INDEX idx_api_keys_user_id ON api_keys (user_id);

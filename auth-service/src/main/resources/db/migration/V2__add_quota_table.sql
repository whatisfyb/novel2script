-- V2: Quota tracking table

CREATE TABLE IF NOT EXISTS user_quota (
    id            VARCHAR(32) PRIMARY KEY,
    user_id       VARCHAR(32) NOT NULL UNIQUE REFERENCES users(id),
    plan          INT         NOT NULL DEFAULT 0,       -- 0=free, 1=pro
    remaining     INT         NOT NULL DEFAULT 10,
    reset_at      TIMESTAMP   NOT NULL,
    created_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_quota_user_id ON user_quota (user_id);

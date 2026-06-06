-- V1: conversion_history table

CREATE TABLE IF NOT EXISTS conversion_history (
    id            VARCHAR(32)  PRIMARY KEY,
    run_id        VARCHAR(64)  NOT NULL,
    user_id       VARCHAR(64),
    filename      VARCHAR(255) NOT NULL,
    title         VARCHAR(255),
    script_type   VARCHAR(32)  NOT NULL,
    language      VARCHAR(16)  NOT NULL,
    status        VARCHAR(16)  NOT NULL DEFAULT 'PROCESSING',
    chapters      INT          DEFAULT 0,
    acts          INT          DEFAULT 0,
    scenes        INT          DEFAULT 0,
    characters    INT          DEFAULT 0,
    yaml          TEXT,
    error         TEXT,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_run_id (run_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS conversion_history (
    id            VARCHAR(32)  PRIMARY KEY,
    run_id        VARCHAR(64)  NOT NULL UNIQUE,
    user_id       VARCHAR(64),
    filename      VARCHAR(255) NOT NULL,
    title         VARCHAR(255),
    script_type   VARCHAR(32)  NOT NULL,
    language      VARCHAR(16)  NOT NULL,
    status        VARCHAR(16)  NOT NULL DEFAULT 'PROCESSING',
    chapters      INTEGER      DEFAULT 0,
    acts          INTEGER      DEFAULT 0,
    scenes        INTEGER      DEFAULT 0,
    characters    INTEGER      DEFAULT 0,
    yaml          TEXT,
    error         TEXT,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversion_history_run_id   ON conversion_history (run_id);
CREATE INDEX idx_conversion_history_user_id  ON conversion_history (user_id);
CREATE INDEX idx_conversion_history_status   ON conversion_history (status);

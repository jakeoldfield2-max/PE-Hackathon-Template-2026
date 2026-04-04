-- Alert tracking table
CREATE TABLE IF NOT EXISTS alert_logs (
    id SERIAL PRIMARY KEY,
    fingerprint VARCHAR(64) UNIQUE NOT NULL,
    alertname VARCHAR(255) NOT NULL,
    instance VARCHAR(255),
    severity VARCHAR(50),
    status VARCHAR(50) NOT NULL,
    summary TEXT,
    description TEXT,
    first_fired_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_alert_logs_status ON alert_logs(status);
CREATE INDEX IF NOT EXISTS idx_alert_logs_alertname ON alert_logs(alertname);
CREATE INDEX IF NOT EXISTS idx_alert_logs_last_updated ON alert_logs(last_updated_at DESC);

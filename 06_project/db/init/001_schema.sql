CREATE TABLE IF NOT EXISTS task_runs (
    id BIGSERIAL PRIMARY KEY,
    task_type VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'queued',
    progress INTEGER NOT NULL DEFAULT 0,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    message TEXT,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT task_runs_task_type_check
        CHECK (task_type IN ('health_check', 'sync_data', 'process_files', 'e2e_test')),
    CONSTRAINT task_runs_status_check
        CHECK (status IN ('queued', 'running', 'success', 'failed', 'cancelled')),
    CONSTRAINT task_runs_progress_check
        CHECK (progress BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS task_logs (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES task_runs(id) ON DELETE CASCADE,
    level VARCHAR(16) NOT NULL DEFAULT 'info',
    message TEXT NOT NULL,
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT task_logs_level_check
        CHECK (level IN ('debug', 'info', 'warning', 'error'))
);

CREATE INDEX IF NOT EXISTS idx_task_runs_status_created_at
    ON task_runs (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_task_runs_task_type_created_at
    ON task_runs (task_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_task_runs_created_at
    ON task_runs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_task_logs_run_id_id
    ON task_logs (run_id, id);

CREATE INDEX IF NOT EXISTS idx_task_logs_level
    ON task_logs (level);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_task_runs_updated_at ON task_runs;

CREATE TRIGGER trg_task_runs_updated_at
    BEFORE UPDATE ON task_runs
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

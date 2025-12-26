-- =============================================================================
-- CLOPUS v3 Short-Term Memory Schema (SQLite)
-- =============================================================================

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- =============================================================================
-- OBJECTIVES
-- =============================================================================
CREATE TABLE IF NOT EXISTS objectives (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'planning', 'in_progress', 'completed', 'failed', 'paused')),
    priority INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSON
);

CREATE INDEX IF NOT EXISTS idx_objectives_status ON objectives(status);
CREATE INDEX IF NOT EXISTS idx_objectives_priority ON objectives(priority DESC);

-- =============================================================================
-- TASKS
-- =============================================================================
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    objective_id TEXT NOT NULL,
    parent_task_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'assigned', 'in_progress', 'validation', 'completed', 'failed', 'blocked')),
    worker_id INTEGER,
    worker_role TEXT,
    priority INTEGER DEFAULT 5,
    dependencies JSON DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result JSON,
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    FOREIGN KEY (objective_id) REFERENCES objectives(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_objective ON tasks(objective_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker_id);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task_id);

-- =============================================================================
-- WORKERS
-- =============================================================================
CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY,
    role TEXT NOT NULL,
    status TEXT DEFAULT 'idle' CHECK (status IN ('idle', 'busy', 'offline', 'error')),
    current_task_id TEXT,
    last_heartbeat TIMESTAMP,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    metadata JSON,
    FOREIGN KEY (current_task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- =============================================================================
-- VALIDATION RESULTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS validation_results (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    stage TEXT NOT NULL CHECK (stage IN ('syntax', 'lint', 'build', 'unit_tests', 'integration_tests', 'e2e_tests', 'security', 'review')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'passed', 'failed', 'skipped')),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    output TEXT,
    errors JSON,
    warnings JSON,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_validation_task ON validation_results(task_id);
CREATE INDEX IF NOT EXISTS idx_validation_stage ON validation_results(stage);

-- =============================================================================
-- QUESTIONS (User Interaction)
-- =============================================================================
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    objective_id TEXT,
    question TEXT NOT NULL,
    context TEXT,
    confidence_score REAL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'answered', 'timeout', 'skipped')),
    answer TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    answered_at TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    FOREIGN KEY (objective_id) REFERENCES objectives(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_questions_status ON questions(status);

-- =============================================================================
-- DECISIONS (Confidence Tracking)
-- =============================================================================
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    decision_type TEXT NOT NULL,
    options JSON NOT NULL,
    chosen_option TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    reasoning TEXT,
    outcome TEXT CHECK (outcome IN ('success', 'failure', 'unknown')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_type ON decisions(decision_type);
CREATE INDEX IF NOT EXISTS idx_decisions_confidence ON decisions(confidence_score);

-- =============================================================================
-- PROJECTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    objective_id TEXT NOT NULL,
    name TEXT NOT NULL,
    repo_url TEXT,
    local_path TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    template_extracted BOOLEAN DEFAULT FALSE,
    metadata JSON,
    FOREIGN KEY (objective_id) REFERENCES objectives(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

-- =============================================================================
-- GENERATED ASSETS
-- =============================================================================
CREATE TABLE IF NOT EXISTS generated_assets (
    id TEXT PRIMARY KEY,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('skill', 'mcp', 'template', 'tool')),
    name TEXT NOT NULL,
    version TEXT DEFAULT '1.0.0',
    source_project_id TEXT,
    local_path TEXT NOT NULL,
    github_synced BOOLEAN DEFAULT FALSE,
    github_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (source_project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_assets_type ON generated_assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_synced ON generated_assets(github_synced);

-- =============================================================================
-- SERVICE INSTANCES (On-Demand Services)
-- =============================================================================
CREATE TABLE IF NOT EXISTS service_instances (
    id TEXT PRIMARY KEY,
    service_name TEXT NOT NULL,
    project_id TEXT,
    container_id TEXT,
    status TEXT DEFAULT 'starting' CHECK (status IN ('starting', 'running', 'stopping', 'stopped', 'error')),
    port_mappings JSON,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stopped_at TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_services_status ON service_instances(status);
CREATE INDEX IF NOT EXISTS idx_services_project ON service_instances(project_id);

-- =============================================================================
-- SESSION STATE
-- =============================================================================
CREATE TABLE IF NOT EXISTS session_state (
    key TEXT PRIMARY KEY,
    value JSON NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- ACTIVITY LOG
-- =============================================================================
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT DEFAULT 'info' CHECK (level IN ('debug', 'info', 'warning', 'error')),
    source TEXT NOT NULL,
    action TEXT NOT NULL,
    details JSON,
    objective_id TEXT,
    task_id TEXT,
    worker_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_activity_level ON activity_log(level);
CREATE INDEX IF NOT EXISTS idx_activity_source ON activity_log(source);

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Active work summary
CREATE VIEW IF NOT EXISTS v_active_work AS
SELECT
    o.id as objective_id,
    o.content as objective,
    o.status as objective_status,
    COUNT(t.id) as total_tasks,
    SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
    SUM(CASE WHEN t.status = 'in_progress' THEN 1 ELSE 0 END) as active_tasks,
    SUM(CASE WHEN t.status = 'failed' THEN 1 ELSE 0 END) as failed_tasks
FROM objectives o
LEFT JOIN tasks t ON t.objective_id = o.id
WHERE o.status NOT IN ('completed', 'failed')
GROUP BY o.id;

-- Worker status summary
CREATE VIEW IF NOT EXISTS v_worker_summary AS
SELECT
    w.id,
    w.role,
    w.status,
    w.tasks_completed,
    w.tasks_failed,
    t.title as current_task,
    w.last_heartbeat,
    CASE
        WHEN w.last_heartbeat IS NULL THEN 'never'
        WHEN (julianday('now') - julianday(w.last_heartbeat)) * 86400 > 30 THEN 'stale'
        ELSE 'recent'
    END as heartbeat_status
FROM workers w
LEFT JOIN tasks t ON t.id = w.current_task_id;

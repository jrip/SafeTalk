-- One-time patch for deployments created before toxicity columns existed.
-- PostgreSQL 11+ (ADD COLUMN IF NOT EXISTS). SQLite: recreate DB or add columns manually.

ALTER TABLE ml_prediction_tasks
    ADD COLUMN IF NOT EXISTS is_toxic boolean;

ALTER TABLE ml_prediction_tasks
    ADD COLUMN IF NOT EXISTS toxicity_probability numeric(10, 8);

ALTER TABLE ml_prediction_tasks
    ADD COLUMN IF NOT EXISTS toxicity_breakdown json;

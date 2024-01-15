BEGIN;

CREATE TABLE IF NOT EXISTS tag_templates (
    template_id VARCHAR (50) NOT NULL,
    template_project VARCHAR (50),
    template_region VARCHAR (50),
    fields JSONB,
    template_uuid VARCHAR (50) PRIMARY KEY NOT NULL
);

CREATE TABLE IF NOT EXISTS shards (
    creation_time TIMESTAMP WITH TIME ZONE,
    job_uuid VARCHAR (50),
    shard_uuid VARCHAR (50) PRIMARY KEY,
    task_count INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    tasks_ran INTEGER DEFAULT 0,
    tasks_running INTEGER DEFAULT 0,
    tasks_success INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tasks (
    config_type VARCHAR (50),
    config_uuid VARCHAR (50),
    creation_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    job_uuid VARCHAR (50),
    shard_uuid VARCHAR,
    start_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR (25),
    task_id VARCHAR (50),
    task_uuid VARCHAR (50) PRIMARY KEY,
    uri VARCHAR (250),
    CONSTRAINT fk_shard
        FOREIGN KEY(shard_uuid)
        REFERENCES shards(shard_uuid)
);

CREATE TABLE IF NOT EXISTS settings (
    setting_type VARCHAR(50) NOT NULL,
    bigquery_dataset VARCHAR (50) NOT NULL,
    bigquery_project VARCHAR (50) NOT NULL,
    bigquery_region VARCHAR (50),
    enabled BOOLEAN
);

CREATE TABLE IF NOT EXISTS jobs (
    completion_time TIMESTAMP WITH TIME ZONE,
    config_type VARCHAR (50),
    config_uuid VARCHAR (50),
    creation_time TIMESTAMP WITH TIME ZONE,
    job_status VARCHAR (25),
    job_uuid VARCHAR (50) PRIMARY KEY,
    task_count INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    tasks_ran INTEGER DEFAULT 0,
    tasks_success INTEGER DEFAULT 0
);



------------ Config Type ------------

CREATE TABLE IF NOT EXISTS static_asset_configs (
    config_uuid VARCHAR (50) PRIMARY KEY,
    config_status VARCHAR (25),
    config_type VARCHAR (50),
    creation_time TIMESTAMP WITH TIME ZONE,
    excluded_assets_uris VARCHAR,
    fields JSONB,
    included_assets_uris VARCHAR,
    included_assets_uris_hash VARCHAR,
    next_run TIMESTAMP WITH TIME ZONE,
    overwrite BOOLEAN,
    refresh_frequency INTEGER,
    refresh_mode VARCHAR (25),
    refresh_unit VARCHAR (25),
    scheduling_status VARCHAR (25),
    service_account VARCHAR,
    tag_history BOOLEAN,
    template_id VARCHAR,
    template_project VARCHAR,
    template_region VARCHAR,
    template_uuid VARCHAR,
    version SMALLINT
);

CREATE TABLE IF NOT EXISTS dynamic_table_configs (
    config_uuid VARCHAR (50) PRIMARY KEY,
    config_status VARCHAR (25),
    config_type VARCHAR (50),
    creation_time TIMESTAMP WITH TIME ZONE,
    excluded_tables_uris VARCHAR,
    fields JSONB,
    included_tables_uris VARCHAR,
    included_tables_uris_hash VARCHAR,
    job_status VARCHAR (25),
    next_run TIMESTAMP WITH TIME ZONE,
    refresh_frequency INTEGER,
    refresh_mode VARCHAR (25),
    refresh_unit VARCHAR (25),
    scheduling_status VARCHAR (25),
    service_account VARCHAR,
    tag_history BOOLEAN,
    template_id VARCHAR,
    template_project VARCHAR,
    template_region VARCHAR,
    template_uuid VARCHAR,
    version SMALLINT
);

CREATE TABLE IF NOT EXISTS dynamic_column_configs (
    config_uuid VARCHAR (50) PRIMARY KEY,
    config_status VARCHAR (25),
    config_type VARCHAR (50),
    creation_time TIMESTAMP WITH TIME ZONE,
    excluded_tables_uris VARCHAR,
    fields JSONB,
    included_columns_query VARCHAR,
    included_tables_uris VARCHAR,
    included_tables_uris_hash VARCHAR,
    job_status VARCHAR (25),
    next_run TIMESTAMP WITH TIME ZONE,
    refresh_frequency INTEGER,
    refresh_mode VARCHAR (25),
    refresh_unit VARCHAR (25),
    scheduling_status VARCHAR (25),
    service_account VARCHAR,
    tag_history BOOLEAN,
    template_id VARCHAR,
    template_project VARCHAR,
    template_region VARCHAR,
    template_uuid VARCHAR,
    version SMALLINT
);

CREATE TABLE IF NOT EXISTS sensitive_column_configs (
    config_uuid VARCHAR (50) PRIMARY KEY,
    config_status VARCHAR (25),
    config_type VARCHAR (50),
    creation_time TIMESTAMP WITH TIME ZONE,
    excluded_tables_uris VARCHAR,
    fields JSONB,
    included_tables_uris VARCHAR,
    included_tables_uris_hash VARCHAR,
    create_policy_tags BOOLEAN,
    infotype_selection_table VARCHAR,
    taxonomy_id VARCHAR,
    dlp_dataset VARCHAR,
    infotype_classification_table VARCHAR,
    next_run TIMESTAMP WITH TIME ZONE,
    refresh_frequency INTEGER,
    refresh_mode VARCHAR (25),
    refresh_unit VARCHAR (25),
    scheduling_status VARCHAR (25),
    overwrite BOOLEAN,
    service_account VARCHAR,
    tag_history BOOLEAN,
    template_id VARCHAR,
    template_project VARCHAR,
    template_region VARCHAR,
    template_uuid VARCHAR,
    version SMALLINT
);

CREATE TABLE IF NOT EXISTS glossary_asset_configs (
    config_uuid VARCHAR (50) PRIMARY KEY,
    config_status VARCHAR (25),
    config_type VARCHAR (50),
    creation_time TIMESTAMP WITH TIME ZONE,
    fields JSONB,
    excluded_assets_uris VARCHAR,
    included_assets_uris VARCHAR,
    included_assets_uris_hash VARCHAR,
    mapping_table VARCHAR,
    next_run TIMESTAMP WITH TIME ZONE,
    refresh_frequency INTEGER,
    refresh_mode VARCHAR (25),
    refresh_unit VARCHAR (25),
    scheduling_status VARCHAR (25),
    overwrite BOOLEAN,
    service_account VARCHAR,
    tag_history BOOLEAN,
    template_id VARCHAR,
    template_project VARCHAR,
    template_region VARCHAR,
    template_uuid VARCHAR,
    version SMALLINT
);

CREATE TABLE IF NOT EXISTS export_configs (
    config_uuid VARCHAR (50) PRIMARY KEY,
    config_status VARCHAR (25),
    config_type VARCHAR (50),
    creation_time TIMESTAMP WITH TIME ZONE,
    write_option VARCHAR,
    target_dataset VARCHAR,
    target_project VARCHAR,
    target_region VARCHAR,
    source_folder VARCHAR,
    source_projects VARCHAR, -- WARNING LIST
    source_region VARCHAR,
    next_run TIMESTAMP WITH TIME ZONE,
    refresh_frequency INTEGER,
    refresh_mode VARCHAR (25),
    refresh_unit VARCHAR (25),
    scheduling_status VARCHAR (25),
    service_account VARCHAR,
    version SMALLINT
);

CREATE TABLE IF NOT EXISTS import_configs (
    config_uuid VARCHAR (50) PRIMARY KEY,
    config_status VARCHAR (25),
    config_type VARCHAR (50),
    creation_time TIMESTAMP WITH TIME ZONE,
    metadata_import_location VARCHAR,
    overwrite BOOLEAN,
    tag_history BOOLEAN,
    service_account VARCHAR,
    template_id VARCHAR,
    template_project VARCHAR,
    template_region VARCHAR,
    template_uuid VARCHAR
);

CREATE TABLE IF NOT EXISTS restore_configs (
    config_uuid VARCHAR (50) PRIMARY KEY,
    config_status VARCHAR (25),
    config_type VARCHAR (50),
    creation_time TIMESTAMP WITH TIME ZONE,
    metadata_export_location VARCHAR,
    target_template_uuid VARCHAR,
    target_template_id VARCHAR,
    target_template_project VARCHAR,
    target_template_region VARCHAR,
    source_template_uuid VARCHAR,
    source_template_id VARCHAR,
    source_template_project VARCHAR,
    source_template_region VARCHAR,
    overwrite BOOLEAN,
    tag_history BOOLEAN,
    service_account VARCHAR
);

CREATE TABLE IF NOT EXISTS entry_configs (
    config_uuid VARCHAR (50) PRIMARY KEY,
    config_status VARCHAR (25),
    config_type VARCHAR (50),
    creation_time TIMESTAMP WITH TIME ZONE,
    fields JSONB,
    excluded_assets_uris VARCHAR,
    included_assets_uris VARCHAR,
    included_assets_uris_hash VARCHAR,
    next_run TIMESTAMP WITH TIME ZONE,
    refresh_frequency INTEGER,
    refresh_mode VARCHAR (25),
    refresh_unit VARCHAR (25),
    scheduling_status VARCHAR (25),
    service_account VARCHAR,
    tag_history BOOLEAN,
    template_id VARCHAR,
    template_project VARCHAR,
    template_region VARCHAR,
    template_uuid VARCHAR,
    version SMALLINT
);



------------ Settings ------------

CREATE TABLE default_settings (
    user_email VARCHAR (250) PRIMARY KEY,
    template_id VARCHAR,
	template_project VARCHAR,
	template_region VARCHAR,
	service_account VARCHAR
);

CREATE TABLE coverage_report_settings (
    included_bigquery_projects VARCHAR,
	excluded_bigquery_datasets VARCHAR,
	excluded_bigquery_tables VARCHAR
);



------------ Optional Settings ------------
CREATE TABLE settings_job_metadata (
    bigquery_dataset VARCHAR (50),
	bigquery_project VARCHAR (50),
	bigquery_region VARCHAR (50),
	enabled BOOLEAN
);

CREATE TABLE settings_tag_history (
    bigquery_dataset VARCHAR (50),
	bigquery_project VARCHAR (50),
	bigquery_region VARCHAR (50),
	enabled BOOLEAN
);

COMMIT;

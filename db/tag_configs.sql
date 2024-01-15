CREATE TABLE IF NOT EXISTS tag_configs (
    config_uuid VARCHAR (50) PRIMARY KEY,
    config_status VARCHAR (25),
    config_type VARCHAR (50),
    creation_time TIMESTAMP WITH TIME ZONE,
    excluded_assets_uris VARCHAR (250),
    excluded_tables_uris VARCHAR (250), -- NEW
    fields JSONB,
    included_assets_uris VARCHAR (250),
    included_assets_uris_hash VARCHAR (250),
    included_tables_uris VARCHAR (250), -- NEW
    included_tables_uris_hash VARCHAR (250), --NEW
    included_columns_query VARCHAR (250), --NEW
    create_policy_tags BOOLEAN, --NEW
    infotype_selection_table VARCHAR (250), --NEW
    taxonomy_id VARCHAR (250), --NEW
    target_template_id VARCHAR (250), --NEW
    source_template_id VARCHAR (250), --NEW
    source_template_region VARCHAR (250), --NEW
    dlp_dataset VARCHAR (250), --NEW
    infotype_classification_table VARCHAR (250), --NEW
    target_dataset VARCHAR (250), --NEW
    target_project VARCHAR (250), --NEW
    metadata_export_location VARCHAR (250), --NEW
    source_folder VARCHAR (250), --NEW
    target_template_project VARCHAR (250), --NEW
    target_region VARCHAR (250), --NEW
    target_template_region VARCHAR (250), --NEW
    target_template_uuid VARCHAR (250), --NEW
    source_template_uuid VARCHAR (250), --NEW
    source_template_project VARCHAR (250), --NEW
    source_region VARCHAR (250), --NEW
    mapping_table VARCHAR (250), --NEW
    write_option VARCHAR (250), --NEW
    metadata_import_location VARCHAR (250), --NEW
    next_run TIMESTAMP WITH TIME ZONE,
    overwrite BOOLEAN,
    refresh_frequency INTEGER,
    refresh_mode VARCHAR (25),
    refresh_unit VARCHAR (25),
    scheduling_status VARCHAR (25),
    service_account VARCHAR (250),
    tag_history BOOLEAN,
    template_id VARCHAR (50),
    template_project VARCHAR (50),
    template_region VARCHAR (50),
    template_uuid VARCHAR,
    version SMALLINT
);
BEGIN;
CREATE INDEX idx1_static_asset_configs ON static_asset_configs (config_status,refresh_mode,scheduling_status,next_run);
CREATE INDEX idx2_static_asset_configs ON static_asset_configs (service_account,config_status);
CREATE INDEX idx3_static_asset_configs ON static_asset_configs (config_type,included_assets_uris_hash,template_uuid,config_status);
CREATE INDEX idx4_static_asset_configs ON static_asset_configs (template_uuid,config_status);

CREATE INDEX idx1_dynamic_column_configs ON dynamic_column_configs (config_status,refresh_mode,scheduling_status,next_run);
CREATE INDEX idx2_dynamic_column_configs ON dynamic_column_configs (service_account,config_status);
CREATE INDEX idx3_dynamic_column_configs ON dynamic_column_configs (config_type,included_tables_uris_hash,template_uuid,config_status);
CREATE INDEX idx4_dynamic_column_configs ON dynamic_column_configs (template_uuid,config_status);

CREATE INDEX idx1_dynamic_table_configs ON dynamic_table_configs (config_status,refresh_mode,scheduling_status,next_run);
CREATE INDEX idx2_dynamic_table_configs ON dynamic_table_configs (service_account,config_status);
CREATE INDEX idx3_dynamic_table_configs ON dynamic_table_configs (config_type,included_tables_uris_hash,template_uuid,config_status);
CREATE INDEX idx4_dynamic_table_configs ON dynamic_table_configs (template_uuid,config_status);

CREATE INDEX idx1_sensitive_column_configs ON sensitive_column_configs (config_status,refresh_mode,scheduling_status,next_run);
CREATE INDEX idx2_sensitive_column_configs ON sensitive_column_configs (service_account,config_status);
CREATE INDEX idx3_sensitive_column_configs ON sensitive_column_configs (config_type,included_tables_uris_hash,template_uuid,config_status);
CREATE INDEX idx4_sensitive_column_configs ON sensitive_column_configs (template_uuid,config_status);

CREATE INDEX idx1_entry_configs ON entry_configs (config_status,refresh_mode,scheduling_status,next_run);
CREATE INDEX idx2_entry_configs ON entry_configs (service_account,config_status);
CREATE INDEX idx3_entry_configs ON entry_configs (config_type,included_assets_uris_hash,template_uuid,config_status);
CREATE INDEX idx4_entry_configs ON entry_configs (template_uuid,config_status);

CREATE INDEX idx1_glossary_asset_configs ON glossary_asset_configs (config_status,refresh_mode,scheduling_status,next_run);
CREATE INDEX idx2_glossary_asset_configs ON glossary_asset_configs (service_account,config_status);
CREATE INDEX idx3_glossary_asset_configs ON glossary_asset_configs (config_type,included_assets_uris_hash,template_uuid,config_status);
CREATE INDEX idx4_glossary_asset_configs ON glossary_asset_configs (template_uuid,config_status);

CREATE INDEX idx1_export_configs ON export_configs (config_status,refresh_mode,scheduling_status,next_run);
CREATE INDEX idx2_export_configs ON export_configs (service_account,config_status);
CREATE INDEX idx3_export_configs ON export_configs (source_projects,source_region,target_dataset,target_project,config_status);

CREATE INDEX idx1_import_configs ON import_configs (config_status,refresh_mode,scheduling_status,next_run);
CREATE INDEX idx2_import_configs ON import_configs (service_account,config_status);
CREATE INDEX idx3_import_configs ON import_configs (template_uuid,config_status);
CREATE INDEX idx4_import_configs ON import_configs (metadata_import_location,template_uuid,config_status);

CREATE INDEX idx1_restore_configs ON restore_configs (config_status,refresh_mode,scheduling_status,next_run);
CREATE INDEX idx2_restore_configs ON restore_configs (service_account,config_status);
CREATE INDEX idx3_restore_configs ON restore_configs (service_account,target_template_uuid,config_status);
CREATE INDEX idx4_restore_configs ON restore_configs (source_template_uuid,target_template_uuid,config_status);

CREATE INDEX idx1_jobs ON jobs (config_uuid);
CREATE INDEX idx2_jobs ON jobs (config_uuid,completion_time);

CREATE INDEX idx1_shards ON shards (job_uuid);

CREATE INDEX idx1_tasks ON tasks (shard_uuid,task_uuid);

CREATE INDEX idx1_tag_templates ON tag_templates (template_id,template_project,template_region);
COMMIT;
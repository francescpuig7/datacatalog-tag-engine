from unittest import TestCase
import TagEngineStoreHandler


class TestTagEngineStoreHandler(TestCase):
    def test_suite(self):
        region = 'europe-west1'
        project = 'fake-project'
        sa = 'fake-project@appspot.gserviceaccount.com'
        bigquery_dataset = 'dataset_name_test'
        user_email = 'fake@dev-test.com'

        print('Starting Test suite')
        test_count = 1
        print(f'{test_count}: Testing connection')
        tcs = TagEngineStoreHandler()
        test_count += 1

        exists, settings = tcs.read_default_settings(user_email=user_email)
        self.assertFalse(exists)
        print(f'{test_count}: read_default_settings --> {exists}, {settings}')
        test_count += 1

        tcs.write_default_settings(user_email, 'template_id', project, region, sa)
        exists, settings = tcs.read_default_settings(user_email=user_email)
        self.assertTrue(exists)
        print(f'{test_count}: Write and read_default_settings --> {exists}, {settings}')
        test_count += 1

        tcs.write_tag_history_settings(True, project, region, bigquery_dataset)
        exists, settings = tcs.read_tag_history_settings()
        self.assertTrue(exists)
        print(f'{test_count}: Write and read tag_history_settings --> {exists}, {settings}')
        test_count += 1

        tcs.write_tag_history_settings(False, project, region, bigquery_dataset)
        exists, settings = tcs.read_tag_history_settings()
        self.assertFalse(exists)
        print(f'{test_count}: Write and read tag_history_settings enabled False--> {exists}, {settings}')
        test_count += 1

        tcs.write_job_metadata_settings(True, project, region, bigquery_dataset)
        exists, settings = tcs.read_job_metadata_settings()
        #self.assertTrue(exists)
        print(f'{test_count}: Write and read job_metadata_settings--> {exists}, {settings}')
        test_count += 1

        tcs.check_active_config('925270c49f3311ee905642004e494302', 'dynamic_tag_column')
        print(f'{test_count}: Check active_config')
        test_count += 1

        template_id = 'data_governance'
        template_uuid = tcs.write_tag_template(template_id, project, region)
        fields = [
        {
            "field_id": "retention_period",
            "field_value": 1.0
        },
        {
            "field_id": "expiration_action",
            "field_value": "Archive"
        },
        {
            "field_id": "manual_overwrite",
            "field_value": True
        }]
        included_assets_uris = f"bigquery/project/{project}/dataset/{bigquery_dataset}/"
        config_uuid = tcs.write_static_asset_config(sa, fields, included_assets_uris, "", template_uuid, template_id,
                                                    project, region, 'AUTO', 24, 'hours', False)
        res = tcs.read_config(sa, config_uuid, 'STATIC_TAG_ASSET')
        print(f"""{test_count}: static asset config--> template_uuid {template_uuid}, config_uuid {config_uuid}. 
        Saved result: {res}""")
        test_count += 1

        print(f"{test_count}: Check active config and increment next run STATIC_TAG_ASSET")
        tcs.check_active_config('915270c49f3311ee905642004e494300', 'SENSITIVE_TAG_COLUMN')
        tcs.increment_version_next_run(sa, config_uuid, 'STATIC_TAG_ASSET')
        test_count += 1

        confs = tcs.read_ready_configs()
        print(f"f{test_count}: Active confs --> {confs}")
        test_count += 1

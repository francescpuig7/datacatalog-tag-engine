# Copyright 2020-2023 Google, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid, pytz, os, requests
import configparser, difflib, hashlib
from datetime import datetime
from datetime import timedelta
from google.cloud import bigquery
import psycopg2
from psycopg2 import extras

import DataCatalogController as controller
import ConfigType as ct
from db.query_builder import dict_to_query


class TagEngineStoreHandler:

    def __init__(self):
        """ Initialize db connection, reading from .ini config
        """
        # read connection parameters
        db_params = self.config()

        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        self.db = psycopg2.connect(**db_params)

    @staticmethod
    def config(filename='tagengine.ini', section='POSTGRESQL'):
        """ Get config data from file .ini
        """
        config = configparser.ConfigParser()
        config.read(filename)

        # get section, default to POSTGRESQL
        db = {}
        if config.has_section(section):
            params = config.items(section)
            for param in params:
                db[param[0]] = param[1]
        else:
            raise Exception('Section {0} not found in the {1} file'.format(section, filename))

        return db

    def read_default_settings(self, user_email):
        """ Read default settings from db
        @return: bool, dict
        """
        settings = {}
        exists = False

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * from default_settings where user_email = '{user_email}'")
            doc_ref = cur.fetchall()
            for row in doc_ref:
                settings = dict(row)
                exists = True

        return exists, settings

    def write_default_settings(self, user_email, template_id, template_project, template_region, service_account):
        """ Write default settings, if user_email exists, update values
        """
        with self.db.cursor() as cur:
            cur.execute(
                f"""INSERT INTO default_settings (user_email, template_id, template_project, template_region, service_account) 
                VALUES ('{user_email}', '{template_id}', '{template_project}', '{template_region}', '{service_account}') 
                ON CONFLICT (user_email) DO UPDATE SET template_id = EXCLUDED.template_id, 
                template_project = EXCLUDED.template_project, template_region = EXCLUDED.template_region, 
                service_account = EXCLUDED.service_account"""
            )
            self.db.commit()
        print('Saved default settings.')

    def read_tag_history_settings(self):
        """ Read settings from db where setting_type is tag_history
        @return: bool, dict
        """
        settings = {}
        enabled = False

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * from settings where setting_type = 'tag_history'")
            doc_ref = cur.fetchall()
            if doc_ref:
                for row in doc_ref:
                    settings = dict(row)
                if settings['enabled']:
                    enabled = True

        return enabled, settings

    def write_tag_history_settings(self, enabled, bigquery_project, bigquery_region, bigquery_dataset):
        """ Write tag_history settings on db
        @return: bool with write_status result
        """
        write_status = True

        with self.db.cursor() as cur:
            try:
                # Preventive delete
                cur.execute("DELETE FROM settings WHERE setting_type = 'tag_history'")
                cur.execute(
                    f"""INSERT INTO settings 
                    (setting_type, enabled, bigquery_project, bigquery_region, bigquery_dataset) 
                    VALUES ('tag_history', {bool(enabled)}, '{bigquery_project}', '{bigquery_region}', 
                    '{bigquery_dataset}')"""
                )
                self.db.commit()
            except Exception as e:
                print('Error occurred during write_tag_history_settings:', e)
                write_status = False

            return write_status

    def read_job_metadata_settings(self):
        """ Read settings from db where setting_type is job_metadata
        @return: bool, dict
        """
        settings = {}
        exists = False

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * from settings where setting_type = 'job_metadata'")
            doc_ref = cur.fetchall()
            for row in doc_ref:
                settings = dict(row)
                exists = True

        return exists, settings

    def write_job_metadata_settings(self, enabled, bigquery_project, bigquery_region, bigquery_dataset):
        """ Write into settings table on db
        @return: bool with write_status result
        """
        write_status = True

        with self.db.cursor() as cur:
            try:
                cur.execute(
                    f"""INSERT INTO settings 
                    (setting_type, enabled, bigquery_project, bigquery_region, bigquery_dataset) 
                    VALUES ('job_metadata', {bool(enabled)}, '{bigquery_project}', '{bigquery_region}', 
                    '{bigquery_dataset}')"""
                )
                self.db.commit()
            except Exception as e:
                print('Error occurred during write_job_metadata_settings:', e)
                write_status = False

            return write_status

    def read_coverage_report_settings(self):
        """ Read coverage_report_settings from db
        @return: bool, dict
        """
        settings = {}
        exists = False

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * from coverage_report_settings")
            doc_ref = cur.fetchall()
            for row in doc_ref:
                settings = dict(row)
                exists = True

        return exists, settings

    def write_coverage_report_settings(self, included_bigquery_projects, excluded_bigquery_datasets, excluded_bigquery_tables):
        """ write coverage report settings on db. make a preventive delete first
        """
        with self.db.cursor() as cur:
            # Preventive delete
            cur.execute("DELETE FROM coverage_report_settings")
            cur.execute(f"""INSERT INTO coverage_report_settings (included_bigquery_projects, excluded_bigquery_datasets, 
            excluded_bigquery_tables) VALUES ('{included_bigquery_projects}', '{excluded_bigquery_datasets}', 
            '{excluded_bigquery_tables}')""")
        print('Saved coverage report settings.')

    def generate_coverage_report(self, credentials):
        """ Generate a coverage report
        @param credentials: creds to interact with datacatalog_v1 library
        @return: list summary_report, list detailed_report
        """
        summary_report = []
        detailed_report = []
        
        exists, settings = self.read_coverage_report_settings()
        included_bigquery_projects = settings['included_bigquery_projects']
        excluded_bigquery_datasets = settings['excluded_bigquery_datasets']
        excluded_bigquery_tables = settings['excluded_bigquery_tables']
        
        print('included_bigquery_projects: ' + included_bigquery_projects)
        print('excluded_bigquery_datasets: ' + excluded_bigquery_datasets)
        print('excluded_bigquery_tables: ' + excluded_bigquery_tables)
        
        # list datasets and tables for chosen projects
        for project in included_bigquery_projects.split(','):
            project_id = project.strip()
            bq_client = bigquery.Client(project=project_id)
            datasets = list(bq_client.list_datasets())
            
            total_tags = 0

            for dataset in datasets:
                
                dataset_id = dataset.dataset_id

                if project_id + "." + dataset_id in excluded_bigquery_datasets:
                    #print('skipping ' + project_id + "." + dataset_id)
                    continue
               
                print("dataset: " + dataset_id)
                
                qualified_dataset = project_id + "." + dataset_id
                overall_sum = 0    
                table_list = []
                tables = list(bq_client.list_tables(dataset_id))
                
                dcc = controller.DataCatalogController(credentials)
                linked_resources = dcc.search_catalog(project_id, dataset_id)
                
                print('linked_resources: ' + str(linked_resources))
            
                for table in tables:
                    print("full_table_id: " + str(table.full_table_id))
                
                    table_path_full = table.full_table_id.replace(':', '/datasets/').replace('.', '/tables/')
                    table_path_short = table.full_table_id.replace(':', '.')
                    table_name = table_path_full.split('/')[4]
                
                    print('table_path_full: ' + table_path_full)
                    print('table_path_short: ' + table_path_short)
                    print('table_name: ' + table_name)
                
                    if table_path_short in project_id + '.' + excluded_bigquery_tables:
                        print('skipping ' + table_path_short)
                        continue
                    
                    if table_name in linked_resources:
                        tag_count = linked_resources[table_name]
                        overall_sum = overall_sum + tag_count
                        print("tag_count = " + str(tag_count))
                        print("overall_sum = " + str(overall_sum))
                
                        # add the table name and tag count to a list 
                        table_list.append((table_name, tag_count))

                # add record to summary report
                summary_record = (qualified_dataset, overall_sum)
                summary_report.append(summary_record)
                detailed_record = {qualified_dataset: table_list}
                detailed_report.append(detailed_record)
        
        return summary_report, detailed_report

    def check_active_config(self, config_uuid, config_type):
        """ Check if config_type with uuid exists
        @return: bool
        """
        coll_name = self.lookup_config_collection(config_type)
        with self.db.cursor() as cur:
            cur.execute(f"""SELECT 1 from {coll_name} where config_uuid = '{config_uuid}'""")
            doc_ref = cur.fetchone()
            if doc_ref:
                return True
            else:
                return False
      
    def update_job_status(self, config_uuid, config_type, status):
        """ Wrapped """
        coll_name = self.lookup_config_collection(config_type)
        if coll_name is None:
            return False
        with self.db.cursor() as cur:
            cur.execute(f"UPDATE {coll_name} SET job_status = '{status}' WHERE config_uuid = '{config_uuid}'")
            self.db.commit()
    
    def update_scheduling_status(self, config_uuid, config_type, status):
        """ Wrapped """
        coll_name = self.lookup_config_collection(config_type)
        with self.db.cursor() as cur:
            try:
                cur.execute(f"UPDATE {coll_name} SET scheduling_status = '{status}' WHERE config_uuid = '{config_uuid}'")
                self.db.commit()
            except Exception:
                print(f'Conf table {coll_name} has no present scheduling_status field')

    def increment_version_next_run(self, service_account, config_uuid, config_type):
        """ Increment +1 in version and set next_run for this config
        """
        config = self.read_config(service_account, config_uuid, config_type)
        
        version = config.get('version', 0) + 1
        delta = config.get('refresh_frequency', 24)
        unit = config.get('refresh_unit', 'hours')
        
        if unit == 'minutes':
            next_run = datetime.utcnow() + timedelta(minutes=delta)
        elif unit == 'hours':
            next_run = datetime.utcnow() + timedelta(hours=delta)
        if unit == 'days':
            next_run = datetime.utcnow() + timedelta(days=delta)
        
        coll_name = self.lookup_config_collection(config_type)

        with self.db.cursor() as cur:
            cur.execute(f"""UPDATE {coll_name} SET version = {version}, next_run = '{next_run}' 
            WHERE config_uuid = '{config_uuid}'""")
            self.db.commit()
                                                                                  
    def read_tag_template_config(self, template_uuid):
        """ Wrapped """
        template_config = None
        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * from tag_templates where template_uuid = '{template_uuid}'")
            res = cur.fetchall()
            for row in res:
                template_config = dict(row)
        return template_config

    def read_tag_template(self, template_id, template_project, template_region):
        """ Wrapped """
        template_exists = False
        template_uuid = ""

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"""SELECT template_uuid FROM tag_templates WHERE template_id = '{template_id}' 
            AND template_project = '{template_project}'
            AND template_region = '{template_region}'""")
            matches = cur.fetchall()

            # should either be a single matching template or no matching templates
            if len(matches) == 1:
                template_uuid = str(dict(matches[0])['template_uuid'])
                print('Tag Template exists. Template uuid: ' + template_uuid)
                template_exists = True

        return template_exists, template_uuid

    def write_tag_template(self, template_id, template_project, template_region):
        """ Wrapped """
        template_exists, template_uuid = self.read_tag_template(template_id, template_project, template_region)
        
        if not template_exists:
            print('tag template {} doesn\'t exist. Creating new template'.format(template_id))
             
            template_uuid = uuid.uuid1().hex
            with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
                cur.execute(f"""INSERT into tag_templates (template_uuid,template_id,template_project,template_region) 
                VALUES ('{template_uuid}','{template_id}','{template_project}','{template_region}')""")

        return template_uuid

    def write_static_asset_config(self, service_account, fields, included_assets_uris, excluded_assets_uris, template_uuid, \
                                  template_id, template_project, template_region, refresh_mode, refresh_frequency, refresh_unit, \
                                  tag_history, overwrite=False):
        """ Wrapped """
        
        print('*** enter write_static_asset_config ***')
        
        # hash the included_assets_uris string
        included_assets_uris_hash = hashlib.md5(included_assets_uris.encode()).hexdigest()

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"""SELECT config_uuid, template_uuid, included_assets_uris_hash, config_type, config_status 
            FROM static_asset_configs WHERE template_uuid = '{template_uuid}' 
            AND included_assets_uris_hash = '{included_assets_uris_hash}'
            AND config_type = 'STATIC_TAG_ASSET'
            AND config_status != 'INACTIVE'""")
            matches = cur.fetchall()

            for match in matches:
                config_uuid_match = dict(match)['config_uuid']
                print('Static config already exists. Config_uuid: ' + str(config_uuid_match))

                # update status to INACTIVE
                cur.execute(f"""UPDATE static_asset_configs SET config_status = 'INACTIVE' 
                WHERE config_uuid = '{config_uuid_match}'""")
                self.db.commit()
                print('Updated config status to INACTIVE.')

            config_uuid = uuid.uuid1().hex

            if refresh_mode == 'AUTO':

                delta, next_run = self.validate_auto_refresh(refresh_frequency, refresh_unit)

                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'STATIC_TAG_ASSET',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'fields': fields,
                    'included_assets_uris': included_assets_uris,
                    'included_assets_uris_hash': included_assets_uris_hash,
                    'excluded_assets_uris': excluded_assets_uris,
                    'template_uuid': template_uuid,
                    'template_id': template_id,
                    'template_project': template_project,
                    'template_region': template_region,
                    'refresh_mode': refresh_mode,  # AUTO refresh mode
                    'refresh_frequency': delta,
                    'refresh_unit': refresh_unit,
                    'tag_history': tag_history,
                    'scheduling_status': 'ACTIVE',
                    'next_run': next_run,
                    'version': 1,
                    'overwrite': overwrite,
                    'service_account': service_account
                }

            else:

                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'STATIC_TAG_ASSET',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'fields': fields,
                    'included_assets_uris': included_assets_uris,
                    'included_assets_uris_hash': included_assets_uris_hash,
                    'excluded_assets_uris': excluded_assets_uris,
                    'template_uuid': template_uuid,
                    'template_id': template_id,
                    'template_project': template_project,
                    'template_region': template_region,
                    'refresh_mode': refresh_mode,  # ON_DEMAND refresh mode
                    'refresh_frequency': 0,  # N/A
                    'tag_history': tag_history,
                    'version': 1,
                    'overwrite': overwrite,
                    'service_account': service_account
                }
            cols, values = dict_to_query(doc_ref)
            query_expr = f"INSERT INTO static_asset_configs {cols} VALUES {values}"
            cur.execute(query_expr)
            self.db.commit()

        print('Created static asset config.')
        
        return config_uuid

    def write_dynamic_table_config(self, service_account, fields, included_tables_uris, excluded_tables_uris, template_uuid, \
                                   template_id, template_project, template_region, refresh_mode, refresh_frequency, \
                                   refresh_unit, tag_history):
        """ Wrapped """

        # hash the included_assets_uris string
        included_tables_uris_hash = hashlib.md5(included_tables_uris.encode()).hexdigest()

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"""SELECT config_uuid FROM dynamic_table_configs WHERE template_uuid = '{template_uuid}' 
            AND included_tables_uris_hash = '{included_tables_uris_hash}'
            AND config_type = 'DYNAMIC_TAG_TABLE'
            AND config_status != 'INACTIVE'""")
            matches = cur.fetchall()

            for match in matches:
                config_uuid_match = dict(match)['config_uuid']
                print('Config already exists. Config_uuid: ' + str(config_uuid_match))

                # update status to INACTIVE
                cur.execute(f"""UPDATE dynamic_table_configs SET config_status = 'INACTIVE' 
                WHERE config_uuid = '{config_uuid_match}'""")
                self.db.commit()
                print('Updated status to INACTIVE.')

            config_uuid = uuid.uuid1().hex

            if refresh_mode == 'AUTO':

                delta, next_run = self.validate_auto_refresh(refresh_frequency, refresh_unit)

                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'DYNAMIC_TAG_TABLE',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'fields': fields,
                    'included_tables_uris': included_tables_uris,
                    'included_tables_uris_hash': included_tables_uris_hash,
                    'excluded_tables_uris': excluded_tables_uris,
                    'template_uuid': template_uuid,
                    'template_id': template_id,
                    'template_project': template_project,
                    'template_region': template_region,
                    'refresh_mode': refresh_mode,  # AUTO refresh mode
                    'refresh_frequency': delta,
                    'refresh_unit': refresh_unit,
                    'tag_history': tag_history,
                    'scheduling_status': 'ACTIVE',
                    'next_run': next_run,
                    'version': 1,
                    'service_account': service_account
                }

            else:
                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'DYNAMIC_TAG_TABLE',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'fields': fields,
                    'included_tables_uris': included_tables_uris,
                    'included_tables_uris_hash': included_tables_uris_hash,
                    'excluded_tables_uris': excluded_tables_uris,
                    'template_uuid': template_uuid,
                    'template_id': template_id,
                    'template_project': template_project,
                    'template_region': template_region,
                    'refresh_mode': refresh_mode,  # ON_DEMAND refresh mode
                    'refresh_frequency': 0,
                    'tag_history': tag_history,
                    'version': 1,
                    'service_account': service_account
                }

            cols, values = dict_to_query(doc_ref)
            query_expr = f"INSERT INTO dynamic_table_configs {cols} VALUES {values}"
            cur.execute(query_expr)
            self.db.commit()
            print('Created dynamic table config.')

        return config_uuid

    def write_dynamic_column_config(self, service_account, fields, included_columns_query, included_tables_uris, excluded_tables_uris, \
                                    template_uuid, template_id, template_project, template_region, \
                                    refresh_mode, refresh_frequency, refresh_unit, tag_history):
        """ Wrapped """
        included_tables_uris_hash = hashlib.md5(included_tables_uris.encode()).hexdigest()

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"""SELECT config_uuid FROM dynamic_column_configs WHERE template_uuid = '{template_uuid}' 
            AND included_tables_uris_hash = '{included_tables_uris_hash}'
            AND config_type = 'DYNAMIC_TAG_COLUMN'
            AND config_status != 'INACTIVE'""")
            matches = cur.fetchall()

            for match in matches:
                config_uuid_match = dict(match)['config_uuid']
                print('Config already exists. Config_uuid: ' + str(config_uuid_match))

                # update status to INACTIVE
                cur.execute(f"""UPDATE dynamic_column_configs SET config_status = 'INACTIVE' 
                WHERE config_uuid = '{config_uuid_match}'""")
                self.db.commit()
                print('Updated status to INACTIVE.')
       
            config_uuid = uuid.uuid1().hex

            if refresh_mode == 'AUTO':

                delta, next_run = self.validate_auto_refresh(refresh_frequency, refresh_unit)

                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'DYNAMIC_TAG_COLUMN',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'fields': fields,
                    'included_columns_query': included_columns_query,
                    'included_tables_uris': included_tables_uris,
                    'included_tables_uris_hash': included_tables_uris_hash,
                    'excluded_tables_uris': excluded_tables_uris,
                    'template_uuid': template_uuid,
                    'template_id': template_id,
                    'template_project': template_project,
                    'template_region': template_region,
                    'refresh_mode': refresh_mode,  # AUTO refresh mode
                    'refresh_frequency': delta,
                    'refresh_unit': refresh_unit,
                    'tag_history': tag_history,
                    'scheduling_status': 'ACTIVE',
                    'next_run': next_run,
                    'version': 1,
                    'service_account': service_account
                }

            else:
                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'DYNAMIC_TAG_COLUMN',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'fields': fields,
                    'included_columns_query': included_columns_query,
                    'included_tables_uris': included_tables_uris,
                    'included_tables_uris_hash': included_tables_uris_hash,
                    'excluded_tables_uris': excluded_tables_uris,
                    'template_uuid': template_uuid,
                    'template_id': template_id,
                    'template_project': template_project,
                    'template_region': template_region,
                    'refresh_mode': refresh_mode,  # ON_DEMAND refresh mode
                    'refresh_frequency': 0,
                    'tag_history': tag_history,
                    'version': 1,
                    'service_account': service_account
                }

            cols, values = dict_to_query(doc_ref)
            query_expr = f"INSERT INTO dynamic_column_configs {cols} VALUES {values}"
            cur.execute(query_expr)
            self.db.commit()
            print('Created dynamic column config.')

        return config_uuid

    def validate_auto_refresh(self, refresh_frequency, refresh_unit):
        """ Wrapped """
        if type(refresh_frequency) is int: 
            if refresh_frequency > 0:
                delta = refresh_frequency
            else:
                delta = 24
        
        if type(refresh_frequency) is str:
            if refresh_frequency.isdigit():
                delta = int(refresh_frequency)
            else:
                delta = 24
        
        if refresh_unit == 'minutes':
            next_run = datetime.utcnow() + timedelta(minutes=delta)    
        elif refresh_unit == 'hours':
            next_run = datetime.utcnow() + timedelta(hours=delta)
        elif refresh_unit == 'days':
            next_run = datetime.utcnow() + timedelta(days=delta)
        else:
            next_run = datetime.utcnow() + timedelta(days=delta) # default to days
            
        return delta, next_run

    def write_entry_config(self, service_account, fields, included_assets_uris, excluded_assets_uris, template_uuid, \
                            template_id, template_project, template_region, refresh_mode, refresh_frequency, \
                            refresh_unit, tag_history):
        """ Wrapped """
        print('** enter write_entry_config **')
        
        included_assets_uris_hash = hashlib.md5(included_assets_uris.encode()).hexdigest()

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"""SELECT config_uuid FROM entry_configs WHERE template_uuid = '{template_uuid}' 
            AND included_assets_uris_hash = '{included_assets_uris_hash}'
            AND config_type = 'ENTRY_CREATE'
            AND config_status != 'INACTIVE'""")
            matches = cur.fetchall()

            for match in matches:
                config_uuid_match = dict(match)['config_uuid']
                print('Tag config already exists. Tag_uuid: ' + str(config_uuid_match))

                # update status to INACTIVE
                cur.execute(f"""UPDATE entry_configs SET config_status = 'INACTIVE' 
                            WHERE config_uuid = '{config_uuid_match}'""")
                self.db.commit()
                print('Updated status to INACTIVE.')
       
            config_uuid = uuid.uuid1().hex
        
            if refresh_mode == 'AUTO':

                delta, next_run = self.validate_auto_refresh(refresh_frequency, refresh_unit)

                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'ENTRY_CREATE',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'fields': fields,
                    'included_assets_uris': included_assets_uris,
                    'included_assets_uris_hash': included_assets_uris_hash,
                    'excluded_assets_uris': excluded_assets_uris,
                    'template_uuid': template_uuid,
                    'template_id': template_id,
                    'template_project': template_project,
                    'template_region': template_region,
                    'refresh_mode': refresh_mode, # AUTO refresh mode
                    'refresh_frequency': delta,
                    'refresh_unit': refresh_unit,
                    'tag_history': tag_history,
                    'scheduling_status': 'ACTIVE',
                    'next_run': next_run,
                    'version': 1,
                    'service_account': service_account
                }

            else:
                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'ENTRY_CREATE',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'fields': fields,
                    'included_assets_uris': included_assets_uris,
                    'included_assets_uris_hash': included_assets_uris_hash,
                    'excluded_assets_uris': excluded_assets_uris,
                    'template_uuid': template_uuid,
                    'template_id': template_id,
                    'template_project': template_project,
                    'template_region': template_region,
                    'refresh_mode': refresh_mode, # ON_DEMAND refresh mode
                    'refresh_frequency': 0,
                    'tag_history': tag_history,
                    'version': 1,
                    'service_account': service_account
                }

            cols, values = dict_to_query(doc_ref)
            query_expr = f"INSERT INTO entry_configs {cols} VALUES {values}"
            cur.execute(query_expr)
            self.db.commit()
            print('Created entry config.')
        
        return config_uuid

    def write_glossary_asset_config(self, service_account, fields, mapping_table, included_assets_uris, excluded_assets_uris, \
                                    template_uuid, refresh_mode, refresh_frequency, refresh_unit, tag_history, \
                                    overwrite=False):
        """ Wrapped """
        print('** enter write_glossary_asset_config **')
        
        included_assets_uris_hash = hashlib.md5(included_assets_uris.encode()).hexdigest()

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"""SELECT config_uuid FROM glossary_asset_configs WHERE template_uuid = '{template_uuid}' 
            AND included_assets_uris_hash = '{included_assets_uris_hash}'
            AND config_type = 'GLOSSARY_TAG_ASSET'
            AND config_status != 'INACTIVE'""")
            matches = cur.fetchall()

            for match in matches:
                config_uuid_match = dict(match)['config_uuid']
                print('Config already exists. Found config_uuid: ' + str(config_uuid_match))

                # update status to INACTIVE
                cur.execute(f"""UPDATE glossary_asset_configs SET config_status = 'INACTIVE' 
                            WHERE config_uuid = '{config_uuid_match}'""")
                self.db.commit()
                print('Updated status to INACTIVE.')
       
            config_uuid = uuid.uuid1().hex
            #TODO: template_id, template_project, template_region
            if refresh_mode == 'AUTO':

                delta, next_run = self.validate_auto_refresh(refresh_frequency, refresh_unit)

                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'GLOSSARY_TAG_ASSET',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'fields': fields,
                    'mapping_table': mapping_table,
                    'included_assets_uris': included_assets_uris,
                    'included_assets_uris_hash': included_assets_uris_hash,
                    'excluded_assets_uris': excluded_assets_uris,
                    'template_uuid': template_uuid,
                    'template_id': template_id,
                    'template_project': template_project,
                    'template_region': template_region,
                    'refresh_mode': refresh_mode, # AUTO refresh mode
                    'refresh_frequency': delta,
                    'refresh_unit': refresh_unit,
                    'tag_history': tag_history,
                    'scheduling_status': 'ACTIVE',
                    'next_run': next_run,
                    'version': 1,
                    'overwrite': overwrite,
                    'service_account': service_account
                }

            else:
                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'GLOSSARY_TAG_ASSET',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'fields': fields,
                    'mapping_table': mapping_table,
                    'included_assets_uris': included_assets_uris,
                    'included_assets_uris_hash': included_assets_uris_hash,
                    'excluded_assets_uris': excluded_assets_uris,
                    'template_uuid': template_uuid,
                    'template_id': template_id,
                    'template_project': template_project,
                    'template_region': template_region,
                    'refresh_mode': refresh_mode, # ON_DEMAND refresh mode
                    'refresh_frequency': 0,
                    'tag_history': tag_history,
                    'version': 1,
                    'overwrite': overwrite,
                    'service_account': service_account
                }

            cols, values = dict_to_query(doc_ref)
            query_expr = f"INSERT INTO glossary_asset_configs {cols} VALUES {values}"
            cur.execute(query_expr)
            self.db.commit()
            print('Created glossary asset config.')

        return config_uuid


    def write_sensitive_column_config(self, service_account, fields, dlp_dataset, infotype_selection_table, infotype_classification_table, \
                                        included_tables_uris, excluded_tables_uris, create_policy_tags, taxonomy_id, template_uuid, \
                                        template_id, template_project, template_region, refresh_mode, refresh_frequency, refresh_unit, \
                                        tag_history, overwrite=False):
        """ Wrapped """
        print('** enter write_sensitive_column_config **')
        
        included_tables_uris_hash = hashlib.md5(included_tables_uris.encode()).hexdigest()

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"""SELECT config_uuid FROM sensitive_column_configs WHERE template_uuid = '{template_uuid}' 
            AND included_tables_uris_hash = '{included_tables_uris_hash}'
            AND config_type = 'SENSITIVE_TAG_COLUMN'
            AND config_status != 'INACTIVE'""")
            matches = cur.fetchall()

            for match in matches:
                config_uuid_match = dict(match)['config_uuid']
                print('Config already exists. Found config_uuid: ' + str(config_uuid_match))

                # update status to INACTIVE
                cur.execute(f"""UPDATE sensitive_column_configs SET config_status = 'INACTIVE' 
                            WHERE config_uuid = '{config_uuid_match}'""")
                self.db.commit()
                print('Updated status to INACTIVE.')
       
            config_uuid = uuid.uuid1().hex

            if refresh_mode == 'AUTO':

                delta, next_run = self.validate_auto_refresh(refresh_frequency, refresh_unit)

                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'SENSITIVE_TAG_COLUMN',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'fields': fields,
                    'dlp_dataset': dlp_dataset,
                    'infotype_selection_table': infotype_selection_table,
                    'infotype_classification_table': infotype_classification_table,
                    'included_tables_uris': included_tables_uris,
                    'included_tables_uris_hash': included_tables_uris_hash,
                    'excluded_tables_uris': excluded_tables_uris,
                    'create_policy_tags': create_policy_tags,
                    'taxonomy_id': taxonomy_id,
                    'template_uuid': template_uuid,
                    'template_id': template_id,
                    'template_project': template_project,
                    'template_region': template_region,
                    'refresh_mode': refresh_mode, # AUTO refresh mode
                    'refresh_frequency': delta,
                    'refresh_unit': refresh_unit,
                    'tag_history': tag_history,
                    'scheduling_status': 'ACTIVE',
                    'next_run': next_run,
                    'version': 1,
                    'overwrite': overwrite,
                    'service_account': service_account
                }

            else:
                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'SENSITIVE_TAG_COLUMN',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'fields': fields,
                    'dlp_dataset': dlp_dataset,
                    'infotype_selection_table': infotype_selection_table,
                    'infotype_classification_table': infotype_classification_table,
                    'included_tables_uris': included_tables_uris,
                    'included_tables_uris_hash': included_tables_uris_hash,
                    'excluded_tables_uris': excluded_tables_uris,
                    'create_policy_tags': create_policy_tags,
                    'taxonomy_id': taxonomy_id,
                    'template_uuid': template_uuid,
                    'template_id': template_id,
                    'template_project': template_project,
                    'template_region': template_region,
                    'refresh_mode': refresh_mode, # ON_DEMAND refresh mode
                    'refresh_frequency': 0,
                    'tag_history': tag_history,
                    'version': 1,
                    'overwrite': overwrite,
                    'service_account': service_account
                }

            cols, values = dict_to_query(doc_ref)
            query_expr = f"INSERT INTO sensitive_column_configs {cols} VALUES {values}"
            cur.execute(query_expr)
            self.db.commit()
            print('Created sensitive column config.')
        
        return config_uuid

    def write_tag_restore_config(self, service_account, source_template_uuid, source_template_id, source_template_project, source_template_region, \
                                 target_template_uuid, target_template_id, target_template_project, target_template_region, \
                                 metadata_export_location, tag_history, overwrite=True):
        """ Wrapped """
        print('** write_tag_restore_config **')

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"""SELECT config_uuid FROM restore_configs WHERE source_template_uuid = '{source_template_uuid}' 
            AND target_template_uuid = '{target_template_uuid}' AND config_status != 'INACTIVE'""")
            matches = cur.fetchall()

            for match in matches:
                config_uuid_match = dict(match)['config_uuid']
                print('Config already exists. Found config_uuid: ' + str(config_uuid_match))

                # update status to INACTIVE
                cur.execute(f"""UPDATE restore_configs SET config_status = 'INACTIVE' 
                            WHERE config_uuid = '{config_uuid_match}'""")
                self.db.commit()
                print('Updated status to INACTIVE.')
       
            config_uuid = uuid.uuid1().hex

            doc_ref = {
                'config_uuid': config_uuid,
                'config_type': 'TAG_RESTORE',
                'config_status': 'ACTIVE',
                'creation_time': datetime.utcnow(),
                'source_template_uuid': source_template_uuid,
                'source_template_id': source_template_id,
                'source_template_project': source_template_project,
                'source_template_region': source_template_region,
                'target_template_uuid': target_template_uuid,
                'target_template_id': target_template_id,
                'target_template_project': target_template_project,
                'target_template_region': target_template_region,
                'metadata_export_location': metadata_export_location,
                'tag_history': tag_history,
                'overwrite': overwrite,
                'service_account': service_account
            }
            cols, values = dict_to_query(doc_ref)
            query_expr = f"INSERT INTO restore_configs {cols} VALUES {values}"
            cur.execute(query_expr)
            self.db.commit()

        return config_uuid

    def write_tag_import_config(self, service_account, template_uuid, template_id, template_project, template_region, \
                                metadata_import_location, tag_history, overwrite=True):
        """ Wrapped """
        print('** write_tag_import_csv_config **')

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"""SELECT config_uuid FROM import_configs WHERE template_uuid = '{template_uuid}' 
            AND metadata_import_location = '{metadata_import_location}' AND config_status != 'INACTIVE'""")
            matches = cur.fetchall()

            for match in matches:
                config_uuid_match = dict(match)['config_uuid']
                print('Config already exists. Found config_uuid: ' + str(config_uuid_match))

                # update status to INACTIVE
                cur.execute(f"""UPDATE import_configs SET config_status = 'INACTIVE' 
                            WHERE config_uuid = '{config_uuid_match}'""")
                self.db.commit()
                print('Updated status to INACTIVE.')
       
            config_uuid = uuid.uuid1().hex

            doc_ref = {
                'config_uuid': config_uuid,
                'config_type': 'TAG_IMPORT',
                'config_status': 'ACTIVE',
                'creation_time': datetime.utcnow(),
                'template_uuid': template_uuid,
                'template_id': template_id,
                'template_project': template_project,
                'template_region': template_region,
                'metadata_import_location': metadata_import_location,
                'tag_history': tag_history,
                'overwrite': overwrite,
                'service_account': service_account
            }
            cols, values = dict_to_query(doc_ref)
            query_expr = f"INSERT INTO import_configs {cols} VALUES {values}"
            cur.execute(query_expr)
            self.db.commit()
        
        return config_uuid

    def write_tag_export_config(self, service_account, source_projects, source_folder, source_region, \
                                target_project, target_dataset, target_region, write_option, \
                                refresh_mode, refresh_frequency, refresh_unit):
        """ Wrapped """
        
        print('** write_tag_export_config **')

        if source_projects != '':
            query_str = f"""SELECT config_uuid FROM export_configs WHERE 
            source_projects = '{source_projects}' 
            AND source_region = '{source_region}'
            AND target_project = '{target_project}'
            AND target_dataset = '{target_dataset}'
            AND config_status != 'INACTIVE'"""
        else:
            query_str = f"""SELECT config_uuid FROM export_configs WHERE 
            source_folder = '{source_folder}' 
            AND source_region = '{source_region}'
            AND target_project = '{target_project}'
            AND target_dataset = '{target_dataset}'
            AND config_status != 'INACTIVE'"""

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(query_str)
            matches = cur.fetchall()

            for match in matches:
                config_uuid_match = dict(match)['config_uuid']
                print('Config already exists. Found config_uuid: ' + str(config_uuid_match))

                # update status to INACTIVE
                cur.execute(f"""UPDATE export_configs SET config_status = 'INACTIVE' 
                WHERE config_uuid = '{config_uuid_match}'""")
                self.db.commit()
                print('Updated status to INACTIVE.')
       
            config_uuid = uuid.uuid1().hex
        
            if refresh_mode == 'AUTO':

                delta, next_run = self.validate_auto_refresh(refresh_frequency, refresh_unit)

                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'TAG_EXPORT',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'source_projects': source_projects,
                    'source_folder': source_folder,
                    'source_region': source_region,
                    'target_project': target_project,
                    'target_dataset': target_dataset,
                    'target_region': target_region,
                    'write_option': write_option,
                    'refresh_mode': refresh_mode,
                    'refresh_frequency': delta,
                    'refresh_unit': refresh_unit,
                    'scheduling_status': 'READY',
                    'next_run': next_run,
                    'version': 1,
                    'service_account': service_account
                }

            else:

                doc_ref = {
                    'config_uuid': config_uuid,
                    'config_type': 'TAG_EXPORT',
                    'config_status': 'ACTIVE',
                    'creation_time': datetime.utcnow(),
                    'source_projects': source_projects,
                    'source_folder': source_folder,
                    'source_region': source_region,
                    'target_project': target_project,
                    'target_dataset': target_dataset,
                    'target_region': target_region,
                    'write_option': write_option,
                    'refresh_mode': refresh_mode, # ON_DEMAND
                    'refresh_frequency': 0,
                    'version': 1,
                    'service_account': service_account
                }
            cols, values = dict_to_query(doc_ref)
            query_expr = f"INSERT INTO export_configs {cols} VALUES {values}"
            cur.execute(query_expr)
            self.db.commit()
            print('Created tag export config.')

        return config_uuid

    @staticmethod
    def lookup_config_collection(requested_ct):
        """ Wrapped """
        coll = None
        
        for available_ct in (ct.ConfigType):
            
            if available_ct.name == requested_ct.strip():
                coll = available_ct.value
        
        return coll

    @staticmethod
    def get_config_collections():
        """ Wrapped """
        colls = []
        for coll in (ct.ConfigType):
            colls.append(coll.value)
        
        return colls
        
    def read_configs(self, service_account, config_type='ALL', template_id=None, template_project=None, template_region=None):
        """ Wrapped """
        print('* enter read_configs *')
        
        colls = []
        pending_running_configs = []
        active_configs = []
        combined_configs = []
        
        if template_id and template_project and template_region:
            template_exists, template_uuid = self.read_tag_template(template_id, template_project, template_region)
        else:
            template_exists = False
            template_uuid = None
        
        if config_type == 'ALL':
            colls = self.get_config_collections()
        else:
            colls.append(self.lookup_config_collection(config_type))

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            for coll_name in colls:
                # skip the export configs because they are tied to a project, not template
                if coll_name == 'export_configs':
                    continue

                query_str = f"""SELECT * FROM {coll_name} WHERE """
                if coll_name == 'restore_configs':
                    if template_exists:
                        query_str += f"target_template_uuid = '{template_uuid}'"
                else:
                    if template_exists:
                        query_str += f"template_uuid = '{template_uuid}'"
                query_str += f" AND config_status != INACTIVE AND service_account = '{service_account}'"

                cur.execute(query_str)
                docs = cur.fetchall()
                for doc in docs:
                    config = dict(doc)

                    if 'job_status' not in config or 'PENDING' in config['job_status'] or 'RUNNING' in config['job_status']:
                        pending_running_configs.append(config)
                    else:
                        active_configs.append(config)

            combined_configs = pending_running_configs + active_configs
        
        return combined_configs

    def read_config(self, service_account, config_uuid, config_type, reformat=False):
        """ Wrapped """
        config_result = {}
        coll_name = self.lookup_config_collection(config_type)

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"""SELECT * from {coll_name} where config_uuid = '{config_uuid}'""")
            res = cur.fetchall()
        
        if res:
            for row in res:
                config_result = dict(row)
            if config_result['service_account'] != service_account:
                return {}
            if reformat and config_type == 'TAG_EXPORT':
                config_result = self.format_source_projects(config_result)

        return config_result

    def read_jobs_by_config(self, config_uuid):
        """ Wrapped """
        job_results = []
        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * from jobs WHERE config_uuid = '{config_uuid}' ORDER BY completion_time DESC")
            jobs_stream = cur.fetchall()

            for job in jobs_stream:
                job_results.append(dict(job))
        
        return job_results

    def read_config_by_job(self, job_uuid):
        """ Wrapped """
        print('read_config_by_job, job_uuid:', job_uuid)
        
        config_uuid = None
        config_type = None

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * from jobs WHERE job_uuid = '{job_uuid}'")
            rows = cur.fetchall()
            for row in rows:
                job = dict(row)
                config_uuid = job['config_uuid']
                config_type = job['config_type']
   
        return config_uuid, config_type

    def read_service_account(self, config_type, config_uuid):
        """ Wrapped """
        service_account = None
        
        coll_name = self.lookup_config_collection(config_type)
        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * from {coll_name} WHERE config_uuid = '{config_uuid}'")
            rows = cur.fetchall()
            for row in rows:
                config = dict(row)
                service_account = config['service_account']
                print(str(config))

        return service_account

    def delete_config(self, service_account, config_uuid, config_type):
        """ Wrapped """
        coll_name = self.lookup_config_collection(config_type)
        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * from {coll_name} WHERE config_uuid = '{config_uuid}'")
            rows = cur.fetchall()
            for row in rows:
                config = dict(row)
                if config['service_account'] != service_account:
                    return False
            try:
                cur.execute(f"DELETE from {coll_name} WHERE config_uuid = '{config_uuid}'")
                self.db.commit()
            except Exception as e:
                print('Error occurred during delete_config: ', e)
                return False
        
        return True

    def purge_inactive_configs(self, service_account, config_type):
        """ Wrapped """
        config_uuids = []
        coll_names = []
        running_count = 0 
        
        if config_type == 'ALL':
            coll_names = self.get_config_collections()
        else:
            coll_names.append(self.lookup_config_collection(config_type))

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            for coll_name in coll_names:
                cur.execute(f"""DELETE from {coll_name} WHERE config_status = 'INACTIVE' 
                AND service_account = '{service_account}' RETURNING *""")
                running_count += int(cur.fetchone())
        
        return running_count

    def read_export_configs(self):
        """ Wrapped """
        
        configs = []
        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute("SELECT * from export_configs WHERE config_status != 'INACTIVE' ORDER BY config_status DESC")
            docs = cur.fetchall()

            for doc in docs:
                config = dict(doc)
                config = self.format_source_projects(config)
                configs.append(config)

        return configs

    @staticmethod
    def format_source_projects(config):
        """ Wrapped """
        if config['source_projects'] != '':

            source_projects = config['source_projects']
            source_projects_str = ''
            for project in source_projects:
                source_projects_str += project + ','

            config['source_projects'] = source_projects_str[0:-1]

        return config

    def read_ready_configs(self):
        """ Get ready active confs
        @return: list from active confs
        """
        ready_configs = []

        for coll_name in self.get_config_collections():
            cur = self.db.cursor(cursor_factory=extras.DictCursor)
            try:
                cur.execute(f"""SELECT * from {coll_name} WHERE refresh_mode = 'AUTO' AND scheduling_status = 'READY' 
                AND config_status = 'ACTIVE' AND next_run <= '{datetime.utcnow()}'""")
                config_stream = cur.fetchall()

                for ready_config in config_stream:
                    config_dict = dict(ready_config)
                    ready_configs.append((config_dict['config_uuid'], config_dict['config_type']))
            except Exception:
                print(f'No active confs for {coll_name}')
            finally:
                cur.close()
        return ready_configs

    def lookup_config_by_uris(self, template_id, template_project, template_region, config_type, included_uris):
        """ Wrapped """
        success = False
        config = None
        config_uuid = ''
        
        template_exists, template_uuid = self.read_tag_template(template_id, template_project, template_region)
        
        if not template_exists:
            print('Error: tag template', template_id, 'does not exist in', template_project, 'and', template_region)
            return success, config_uuid
        
        coll_name = self.lookup_config_collection(config_type)
        
        if 'asset' in coll_name:
            query_str = f"""SELECT config_uuid FROM '{coll_name}' WHERE 
            template_uuid = '{template_uuid}' 
            AND config_status = 'ACTIVE' 
            AND included_assets_uris = '{included_uris}'"""
        else:
            query_str = f"""SELECT config_uuid FROM '{coll_name}' WHERE 
            template_uuid = '{template_uuid}' 
            AND config_status = 'ACTIVE' 
            AND included_tables_uris = '{included_uris}'"""

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(query_str)
            config = cur.fetchall()

            if not config:
                print('Error: config could not be found')
                return success, config_uuid
            else:
                if len(config) == 1:
                    config_uuid = dict(config[0]['config_uuid'])
                    success = True

        return success, config_uuid

    def lookup_tag_template(self, config_type, config_uuid):
        """ Wrapped """
        template_id = None

        coll_name = self.lookup_config_collection(config_type)
        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * from {coll_name} WHERE config_uuid = '{config_uuid}'")
            docs = cur.fetchall()

            if docs:
                for doc in docs:
                    config = dict(doc)
                    template_id = config['template_id']
            else:
                print('Error: could not locate the config')

        return template_id

    def lookup_service_account(self, config_type, config_uuid):
        """ Wrapped """
        service_account = None

        coll_name = self.lookup_config_collection(config_type)
        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * from {coll_name} WHERE config_uuid = '{config_uuid}'")
            docs = cur.fetchall()

            if docs:
                for doc in docs:
                    config = dict(doc)
                    service_account = config['service_account']
            else:
                print('Error: could not locate the config, returning an empty service account')

        return service_account

    def update_config(self, old_config_uuid, config_type, config_status, fields, included_uris, excluded_uris, template_uuid, \
                      template_id, template_project, template_region, refresh_mode, refresh_frequency, \
                      refresh_unit, tag_history, overwrite=False, mapping_table=None):
        """ Wrapped """
        print('enter update_config')
        print('old_config_uuid: ', old_config_uuid)
        print('config_type: ', config_type)
        
        coll_name = self.lookup_config_collection(config_type)
        print('coll_name: ', coll_name)

        with self.db.cursor() as cur:
            cur.execute(f"UPDATE {coll_name} SET config_status = 'INACTIVE' WHERE config_uuid = '{old_config_uuid}'")
            self.db.commit()
        
        if config_type == 'STATIC_TAG_ASSET':
            new_config_uuid = self.write_static_asset_config(config_status, fields, included_uris, excluded_uris, template_uuid, \
                                                             template_id, template_project, template_region, \
                                                             refresh_mode, refresh_frequency, refresh_unit, \
                                                             tag_history, overwrite)
        
        if config_type == 'DYNAMIC_TAG_TABLE':
            new_config_uuid = self.write_dynamic_table_config(config_status, fields, included_uris, excluded_uris, \
                                                            template_uuid, template_id, template_project, template_region, \
                                                            refresh_mode, refresh_frequency, refresh_unit, tag_history)
                
        if config_type == 'ENTRY_CREATE':
            new_config_uuid = self.write_entry_config(config_status, fields, included_uris, excluded_uris, \
                                                      template_uuid, template_id, template_project, template_region, 
                                                      refresh_mode, refresh_frequency, refresh_unit, tag_history)
                                                                     
        if config_type == 'GLOSSARY_TAG_ASSET':
            new_config_uuid = self.write_glossary_asset_config(config_status, fields, mapping_table, included_uris, excluded_uris, \
                                                               template_uuid, template_id, template_project, template_region, \
                                                               refresh_mode, refresh_frequency, refresh_unit, tag_history, overwrite)
        # note: no need to return the included_uris_hash
            
        return new_config_uuid

    def update_dynamic_column_config(self, old_config_uuid, config_type, config_status, fields, included_columns_query, included_tables_uris,\
                                     excluded_tables_uris, template_uuid, template_id, template_project, template_region, \
                                     refresh_mode, refresh_frequency, refresh_unit, tag_history):
        """ Wrapped """
        with self.db.cursor() as cur:
            cur.execute(f"""UPDATE dynamic_column_configs SET config_status = 'INACTIVE' 
            WHERE config_uuid = '{old_config_uuid}'""")
            self.db.commit()

        new_config_uuid, included_tables_uris_hash = self.write_dynamic_column_config(config_status, fields, included_columns_query, \
                                                              included_tables_uris, excluded_tables_uris, \
                                                              template_uuid, template_id, template_project, template_region, \
                                                              refresh_mode, refresh_frequency, refresh_unit, tag_history)
        
        return new_config_uuid

    def update_sensitive_column_config(self, old_config_uuid, config_status, dlp_dataset, infotype_selection_table, \
                                       infotype_classification_table, included_tables_uris, excluded_tables_uris, \
                                       create_policy_tags, taxonomy_id, template_uuid, template_id, template_project, template_region, \
                                       refresh_mode, refresh_frequency, refresh_unit, tag_history, overwrite):
        """ Wrapped """
        with self.db.cursor() as cur:
            cur.execute(f"""UPDATE sensitive_column_configs SET config_status = 'INACTIVE' 
            WHERE config_uuid = '{old_config_uuid}'""")
            self.db.commit()
        
        config = self.read_config(old_config_uuid, 'SENSITIVE_TAG_COLUMN') # TODO: number parameters read_config
        
        new_config_uuid, included_tables_uris_hash = self.write_sensitive_column_config(config_status, config['fields'], dlp_dataset, \
                                                                          infotype_selection_table, infotype_classification_table, \
                                                                          included_tables_uris, excluded_tables_uris, \
                                                                          create_policy_tags, taxonomy_id, template_uuid, \
                                                                          template_id, template_project, template_region, \
                                                                          refresh_mode, refresh_frequency, refresh_unit, \
                                                                          tag_history, overwrite)

        return new_config_uuid

    def update_tag_restore_config(self, old_config_uuid, config_status, source_template_uuid, source_template_id, source_template_project, 
                              source_template_region, target_template_uuid, target_template_id, target_template_project, \
                              target_template_region, metadata_export_location, tag_history, overwrite=False):
        """ Wrapped """
        with self.db.cursor() as cur:
            cur.execute(f"""UPDATE restore_configs SET config_status = 'INACTIVE' 
            WHERE config_uuid = '{old_config_uuid}'""")
            self.db.commit()
        
        new_config_uuid = self.write_tag_restore_config(config_status, source_template_uuid, source_template_id, source_template_project, \
                                                        source_template_region, target_template_uuid, target_template_id, \
                                                        target_template_project, target_template_region, \
                                                        metadata_export_location, tag_history, overwrite)

        return new_config_uuid

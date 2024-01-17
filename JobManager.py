# Copyright 2022-2023 Google, LLC.
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

import uuid, datetime, json, configparser
import constants
import psycopg2
from psycopg2 import extras
from google.cloud import tasks_v2
from db.query_builder import dict_to_query

class JobManager:
    """Class for managing jobs for async task create and update requests
    
    cloud_run_sa = Cloud Run service account
    project = Cloud Run project id (e.g. tag-engine-project)
    region = Cloud Run region (e.g. us-central1)
    queue_name = Cloud Task queue (e.g. tag-engine-queue)
    task_handler_uri = task handler uri in the Flask app hosted by Cloud Run 
    
    """
    def __init__(self,
                cloud_run_sa,
                tag_engine_project,
                queue_region,
                queue_name, 
                task_handler_uri,
                db_params=None):

        self.cloud_run_sa = cloud_run_sa
        self.tag_engine_project = tag_engine_project
        self.queue_region = queue_region
        self.queue_name = queue_name
        self.task_handler_uri = task_handler_uri
        self.db = psycopg2.connect(**db_params)


##################### API METHODS #################

    def create_job(self, tag_creator_account, tag_invoker_account, config_uuid, config_type, metadata=None):
        
        print('*** enter create_job ***')
        print('config_uuid: ', config_uuid, ', config_type: ', config_type)
        
        job_uuid = self._create_job_record(config_uuid, config_type)
        
        if metadata != None:
            self._create_job_metadata_record(job_uuid, config_uuid, config_type, metadata)
        
        resp = self._create_job_task(tag_creator_account, tag_invoker_account, job_uuid, config_uuid, config_type)
                
        return job_uuid

    def update_job_running(self, job_uuid):

        print('*** update_job_running ***')

        with self.db.cursor() as cur:
            cur.execute(f"UPDATE jobs SET job_status = 'RUNNING' WHERE job_uuid = '{job_uuid}'")
            self.db.commit()
        
        print('Set job running.')

    def record_num_tasks(self, job_uuid, num_tasks):
        
        print('*** enter record_num_tasks ***')

        with self.db.cursor() as cur:
            cur.execute(f"UPDATE jobs SET task_count = {num_tasks} WHERE job_uuid = '{job_uuid}'")
            self.db.commit()
        
        print('record_num_tasks')

    def calculate_job_completion(self, job_uuid):
        
        print('*** enter calculate_job_completion ***')

        tasks_success = self._get_tasks_success(job_uuid)
        tasks_failed = self._get_tasks_failed(job_uuid)
              
        tasks_ran = tasks_success + tasks_failed
        
        print('tasks_success:', tasks_success)
        print('tasks_failed:', tasks_failed)
        print('tasks_ran:', tasks_ran)

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * FROM jobs WHERE job_uuid = '{job_uuid}'")
            jobs = cur.fetchall()

            for job in jobs:
                job_dict = dict(job)
                task_count = job_dict['task_count']

                # job running
                if job_dict['task_count'] > tasks_ran:

                    t_ran = tasks_success + tasks_failed
                    cur.execute(f"""UPDATE jobs SET tasks_ran = {t_ran}, job_status = 'RUNNING', 
                    tasks_success = {tasks_success}, tasks_failed = {tasks_failed} WHERE job_uuid = '{job_uuid}'""")
                    self.db.commit()

                    pct_complete = round(tasks_ran / task_count * 100, 2)

                # job completed
                if job_dict['task_count'] <= tasks_ran:

                    if tasks_failed > 0:
                        t_ran = tasks_success + tasks_failed
                        cur.execute(f"""UPDATE jobs SET tasks_ran = {t_ran}, job_status = 'ERROR', 
                        tasks_success = {tasks_success}, tasks_failed = {tasks_failed}, 
                        completion_time = {datetime.datetime.utcnow()} WHERE job_uuid = '{job_uuid}'""")
                        self.db.commit()

                    else:
                        t_ran = tasks_success + tasks_failed
                        cur.execute(f"""UPDATE jobs SET tasks_ran = {t_ran}, job_status = 'SUCCESS', 
                        tasks_success = {tasks_success}, tasks_failed = {tasks_failed}, 
                        completion_time = {datetime.datetime.utcnow()} WHERE job_uuid = '{job_uuid}'""")
                        self.db.commit()

                    pct_complete = 100

        return tasks_success, tasks_failed, pct_complete

    def get_job_status(self, job_uuid):

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT * FROM jobs WHERE job_uuid = '{job_uuid}'")
            jobs = cur.fetchall()

            for job in jobs:
                return dict(job)

    def set_job_status(self, job_uuid, status):

        with self.db.cursor() as cur:
            cur.execute(f"UPDATE jobs SET job_status = '{status}' WHERE job_uuid = '{job_uuid}'")
            self.db.commit()


################ INTERNAL PROCESSING METHODS #################

    def _create_job_record(self, config_uuid, config_type):
        
        print('*** _create_job_record ***')
        
        job_uuid = uuid.uuid1().hex

        with self.db.cursor() as cur:
            job_ref = {
                'job_uuid': job_uuid,
                'config_uuid': config_uuid,
                'config_type': config_type,
                'job_status':  'PENDING',
                'task_count': 0,
                'tasks_ran': 0,
                'tasks_success': 0,
                'tasks_failed': 0,
                'creation_time': datetime.datetime.utcnow()
            }
            cols, values = dict_to_query(job_ref)
            cur.execute(f"INSERT INTO jobs {cols} VALUES {values}")
            self.db.commit()
        
        print('Created job record.')
    
        return job_uuid

    def _create_job_task(self, tag_creator_account, tag_invoker_account, job_uuid, config_uuid, config_type):
        
        print('*** enter _create_cloud_task ***')
                
        payload = {'job_uuid': job_uuid, 'config_uuid': config_uuid, 'config_type': config_type, \
                   'tag_creator_account': tag_creator_account, 'tag_invoker_account': tag_invoker_account}
        
        task = {
            'http_request': {  
                'http_method': 'POST',
                'url': self.task_handler_uri,
                'headers': {'content-type': 'application/json'},
                'body': json.dumps(payload).encode(),
                'oidc_token': {'service_account_email': self.cloud_run_sa, 'audience': self.task_handler_uri}
            }
        }
        
        #print('task create:', task)
        
        client = tasks_v2.CloudTasksClient()
        parent = client.queue_path(self.tag_engine_project, self.queue_region, self.queue_name)
        resp = client.create_task(parent=parent, task=task)
        #print('task resp: ', resp)
        
        return resp
      

    def _get_task_count(self, job_uuid):
        
        print('*** enter _get_task_count ***')

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"SELECT task_count FROM jobs WHERE job_uuid = '{job_uuid}'")
            jobs = cur.fetchall()

            for job in jobs:
                return dict(job).get('task_count')

    def _get_tasks_success(self, job_uuid):
        
        tasks_success = 0

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"""SELECT tasks_success FROM shards WHERE job_uuid = '{job_uuid}'""")
            shards = cur.fetchall()

            for shard in shards:
                tasks_success += dict(shard).get('tasks_success', 0)
        
        return tasks_success

    def _get_tasks_failed(self, job_uuid):

        tasks_failed = 0

        with self.db.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(f"""SELECT tasks_failed FROM shards WHERE job_uuid = '{job_uuid}'""")
            shards = cur.fetchall()

            for shard in shards:
                tasks_failed += dict(shard).get('tasks_failed', 0)

        return tasks_failed

    def _create_job_metadata_record(self, job_uuid, config_uuid, config_type, metadata):

        print('*** _create_job_metadata_record ***')

        with self.db.cursor() as cur:
            job_ref = {
                'job_uuid': job_uuid,
                'config_uuid': config_uuid,
                'config_type': config_type,
                'metadata': metadata,
                'creation_time': datetime.datetime.utcnow()
            }
            cols, values = dict_to_query(job_ref)
            cur.execute(f"INSERT INTO job_metadata {cols} VALUES {values}")
            self.db.commit()
        print('Created job_metadata record.')
    
        
if __name__ == '__main__':

    config = configparser.ConfigParser()
    config.read("tagengine.ini")
    
    project = config['DEFAULT']['PROJECT']
    region = config['DEFAULT']['REGION']
    queue_name = config['DEFAULT']['INJECTOR_QUEUE']
    db_name = config['DEFAULT'].get('DB_NAME', None)
    task_handler_uri = '/_split_work'

    # get section, default to POSTGRESQL
    db_params = {}
    if config.has_section('POSTGRESQL'):
        params = config.items('POSTGRESQL')
        for param in params:
            db_params[param[0]] = param[1]

    jm = JobManager(project, region, queue_name, task_handler_uri, db_params)
    
    config_uuid = '1f1b4720839c11eca541e1ad551502cb'
    jm.create_async_job(config_uuid)
    
    print('done')



    

    

            
        

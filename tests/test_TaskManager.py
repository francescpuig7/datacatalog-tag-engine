from unittest import TestCase
import TaskManager
import JobManager


class TestTaskManager(TestCase):
    def test_suite(self):
        region = 'europe-west1'
        project = 'fake-project'
        sa = 'fake-project@appspot.gserviceaccount.com'
        queue_name = 'fake_queue'

        print('Starting Test suite')
        test_count = 1
        print(f'{test_count}: Testing connection')
        tm = TaskManager(sa, project, region, queue_name, 'localhost')
        jm = JobManager(sa, project, region, queue_name, 'localhost')
        test_count += 1

        config_uuid = 'd2as5fds63as2sd5f09'
        job_uuid = jm._create_job_record(config_uuid, 'TEST_TYPE')
        jm.record_num_tasks(job_uuid, 1)
        jm.update_job_running(job_uuid)
        tm.create_config_uuid_tasks(sa, sa, job_uuid, config_uuid, 'TEST_TYPE', ['localhost:80', 'localhost:8080'])
        print(f'{test_count}: create_config_uuid_tasks job_uuid--> {job_uuid}')
        test_count += 1

        shard_uuid = '139psolk57asp2447e2'
        tm._create_shard(job_uuid, shard_uuid)
        tm._update_shard_tasks(job_uuid, shard_uuid, 5)
        tm._set_rollup_tasks_success(shard_uuid)
        print(f'{test_count}: create and rullup shard/tasks shard_uuid --> {shard_uuid}')
        test_count += 1

        task_uuid = tm._record_config_uuid_task(
            job_uuid + "9", shard_uuid, 'task_id', config_uuid, 'TEST_TYPE', 'localhost')
        self.assertIsInstance(task_uuid, str)
        print(f'{test_count}: _record_config_uuid_task task_uuid --> {task_uuid}')

from unittest import TestCase
import JobManager


class TestJobManager(TestCase):
    def test_suite(self):
        region = 'europe-west1'
        project = 'fake-project'
        sa = 'fake-project@appspot.gserviceaccount.com'
        queue_name = 'fake_queue'

        print('Starting Test suite')
        test_count = 1
        print(f'{test_count}: Testing connection')
        jm = JobManager(sa, project, region, queue_name, 'localhost')
        test_count += 1

        job_uuid = jm._create_job_record('5f45a512fsd252sa5w', 'CONFIG_TYPE')
        self.assertIsInstance(job_uuid, str)
        print(f'{test_count}: create_job_record --> {job_uuid}')
        test_count += 1

        total = jm._get_task_count(job_uuid)
        succ = jm._get_tasks_success(job_uuid)
        fail = jm._get_tasks_failed(job_uuid)
        self.assertIsInstance(total, int)
        self.assertIsInstance(succ, int)
        self.assertIsInstance(fail, int)
        print(f'{test_count}: Get tasks --> success {succ}, failed {fail}, total {total}')
        test_count += 1

        jm.set_job_status(job_uuid, 'SUCCESS')
        jm.record_num_tasks(job_uuid, 1)
        total = jm._get_task_count(job_uuid)
        jm.calculate_job_completion(job_uuid)
        self.assertEqual(total, 1)
        print(f'{test_count}: Updatet total tasks --> {total}')

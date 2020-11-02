import os
import unittest

from appian_locust import AppianTaskSet
from appian_locust._tasks import _Tasks
from locust import Locust, TaskSet

from tests.mock_client import CustomLocust
from tests.mock_reader import read_mock_file


class TestTask(unittest.TestCase):

    task_feed_resp = read_mock_file("tasks_response.json")
    task_feed_with_next = read_mock_file("tasks_response_with_next.json")

    def get_task_attributes(self, is_auto_acceptable: bool) -> str:
        return f"""
        {{
            "isOfflineTask": false,
            "isSailTask": true,
            "isQuickTask": false,
            "taskId": "1",
            "isAutoAcceptable": {'true' if is_auto_acceptable else 'false'}
        }}"""

    def setUp(self) -> None:
        self.custom_locust = CustomLocust(Locust())
        parent_task_set = TaskSet(self.custom_locust)
        setattr(parent_task_set, "host", "")
        setattr(parent_task_set, "auth", ["", ""])
        self.task_set = AppianTaskSet(parent_task_set)
        self.task_set.host = ""

        # test_on_start_auth_success is covered here.
        self.custom_locust.set_response("auth?appian_environment=tempo", 200, '{}')
        self.custom_locust.set_default_response(200, "{}")
        self.task_set.on_start()
        self.custom_locust.set_response(
            "/suite/rest/a/task/latest/1/attributes",
            200,
            self.get_task_attributes(is_auto_acceptable=True))
        self.custom_locust.set_response(_Tasks.INITIAL_FEED_URI, 200, self.task_feed_resp)

    def tearDown(self) -> None:
        self.task_set.on_stop()

    def test_task_get_all(self) -> None:
        self.custom_locust.enqueue_response(200, self.task_feed_with_next)
        self.custom_locust.enqueue_response(200, self.task_feed_resp)
        all_task = self.task_set.appian.tasks.get_all()

        self.assertEqual(len(all_task.keys()), 21)
        # TODO: These keys are bad, as are the record/ report keys, consider just using the names/ IDs
        self.assertEqual(all_task['t-2109072_34 Task_Assign SR#0G56-W7N3 to Case Worker']['id'], 't-2109072')

    def test_task_get(self) -> None:
        task = self.task_set.appian.tasks.get_task(
            "t-1", False)
        self.assertIsInstance(task, dict)

    def test_task_get_missing_task(self) -> None:
        with self.assertRaisesRegex(Exception, "There is no task with name .* in the system under test.*"):
            self.task_set.appian.tasks.get_task("some random word")

    def test_task_visit(self) -> None:
        output = self.task_set.appian.tasks.visit("t-1", False)
        self.assertEqual(output, {})

    def test_task_visit_and_get_form(self) -> None:
        task_to_accept = read_mock_file('task_accept_resp.json')
        self.custom_locust.set_response(
            "/suite/rest/a/task/latest/1/status",
            200,
            task_to_accept
        )
        self.custom_locust.set_response(
            "/suite/rest/a/task/latest/1/attributes",
            200,
            self.get_task_attributes(is_auto_acceptable=False))
        output = self.task_set.appian.tasks.visit_and_get_form("t-1", False)

        self.assertEqual(output.form_url, "/suite/rest/a/task/latest/1/status")


if __name__ == '__main__':
    unittest.main()

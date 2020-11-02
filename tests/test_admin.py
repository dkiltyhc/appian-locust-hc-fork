from locust import TaskSet, Locust
from .mock_client import CustomLocust
from .mock_reader import read_mock_file
from appian_locust import AppianTaskSet
from appian_locust.uiform import (SailUiForm)
from appian_locust.helper import ENV
import unittest


class TestAdmin(unittest.TestCase):
    def setUp(self) -> None:
        self.custom_locust = CustomLocust(Locust())
        parent_task_set = TaskSet(self.custom_locust)
        setattr(parent_task_set, "host", "")
        setattr(parent_task_set, "auth", ["", ""])
        self.task_set = AppianTaskSet(parent_task_set)
        self.task_set.host = ""

        # test_on_start_auth_success is covered here.
        self.custom_locust.set_response("auth?appian_environment=tempo", 200, '{}')
        self.task_set.on_start()

    def test_visit(self) -> None:
        self.custom_locust.set_response("/suite/rest/a/applications/latest/app/admin", 200, read_mock_file("admin_console_landing_page.json"))
        ENV.stats.clear_all()
        sail_form = self.task_set.appian.admin.visit()
        self.assertEqual(type(sail_form), SailUiForm)
        self.assertEqual(0, len(ENV.stats.errors))

    def test_visit_error(self) -> None:
        ENV.stats.clear_all()
        self.custom_locust.set_response("/suite/rest/a/applications/latest/app/admin", 400, "")
        with self.assertRaises(Exception) as context:
            sail_form = self.task_set.appian.admin.visit()
        # Two errors will be logged, one at the get_page request level, and one at the visit
        self.assertEqual(2, len(ENV.stats.errors))


if __name__ == '__main__':
    unittest.main()

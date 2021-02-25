import unittest

import locust
from appian_locust import AppianTaskSet
from appian_locust.helper import ENV
from appian_locust.uiform import SailUiForm
from locust import Locust, TaskSet

from .mock_client import CustomLocust
from .mock_reader import read_mock_file


class TestAdmin(unittest.TestCase):
    def setUp(self) -> None:
        self.custom_locust = CustomLocust(Locust())
        parent_task_set = TaskSet(self.custom_locust)
        setattr(parent_task_set, "host", "")
        setattr(parent_task_set, "auth", ["admin_user", ""])
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
        self.custom_locust.set_response("/suite/rest/a/applications/latest/app/admin", 401, "")
        with self.assertRaises(Exception) as context:
            sail_form = self.task_set.appian.admin.visit()
        # Two errors will be logged, one at the get_page request level, and one at the visit
        self.assertEqual(2, len(ENV.stats.errors))

        # Assert error structure
        error: locust.stats.StatsError = list(ENV.stats.errors.values())[1]
        self.assertEqual('DESC: No description', error.method)
        self.assertEqual('LOCATION: _admin.py/visit()', error.name)
        self.assertEqual('EXCEPTION: HTTP ERROR CODE: 401 MESSAGE:  USERNAME: admin_user', error.error)
        self.assertEqual(1, error.occurrences)


if __name__ == '__main__':
    unittest.main()

import json
import os
import unittest
from unittest.mock import Mock

# Testing various imports rerouted
from appian_locust import AppianClient, AppianTaskSet, helper, appianclient, records_helper, uiform, logger
from appian_locust.exceptions import BadCredentialsException, MissingCsrfTokenException, MissingConfigurationException
from appian_locust.appianclient import procedurally_generate_credentials, setup_distributed_creds
from locust import Locust, TaskSet

from .mock_client import CustomLocust, MockClient, SampleAppianTaskSequence
from .mock_reader import read_mock_file

log = logger.getLogger(__name__)


class TestAppianBase(unittest.TestCase):

    dir_path = os.path.dirname(os.path.realpath(__file__))
    form_content = read_mock_file("form_content_response.json")
    form_content_2 = read_mock_file("sites_record_nav.json")
    form_content_3 = read_mock_file("sites_record_recordType_resp.json")
    nested_dynamic_link_json = read_mock_file("nested_dynamic_link_response.json")

    def setUp(self) -> None:
        self.custom_locust = CustomLocust(Locust())
        self.parent_task_set = TaskSet(self.custom_locust)
        setattr(self.parent_task_set, "host", "")
        setattr(self.parent_task_set, "credentials", [["", ""]])
        setattr(self.parent_task_set, "auth", ["a", "b"])

        self.task_set = AppianTaskSet(self.parent_task_set)
        self.task_set.host = ""

        self.task_set.on_start()

    def tearDown(self) -> None:
        if '__appianMultipartCsrfToken' in self.task_set.appian.client.cookies:
            self.task_set.on_stop()

    def test_determine_auth_with_only_auth_key(self) -> None:
        # Given
        for bad_creds in [[], "", None, 30]:
            setattr(self.parent_task_set, "credentials", bad_creds)

            # When
            auth = self.task_set.determine_auth()

            # Then
            self.assertEqual(["a", "b"], auth)

    def test_determine_auth_with_only_credentials_key(self) -> None:
        # Given
        setattr(self.parent_task_set, "auth", "")
        setattr(self.parent_task_set, "credentials", [["aa", "bb"], ["c", "d"]])

        # When the first hit is done
        auth1 = self.task_set.determine_auth()
        auth2 = self.task_set.determine_auth()
        auth3 = self.task_set.determine_auth()
        auth4 = self.task_set.determine_auth()

        # Then
        self.assertEqual(["aa", "bb"], auth1)  # Pop is FIFO
        self.assertEqual(["c", "d"], auth2)
        self.assertEqual(["c", "d"], auth3)
        self.assertEqual(["c", "d"], auth4)

    def test_determine_auth_with_credentials_and_auth_keys(self) -> None:
        # Given
        setattr(self.parent_task_set, "credentials", [["aa", "bb"], ["c", "d"]])

        # When the first hit is done
        auth1 = self.task_set.determine_auth()
        auth2 = self.task_set.determine_auth()
        auth3 = self.task_set.determine_auth()
        auth4 = self.task_set.determine_auth()

        # Then
        self.assertEqual(["aa", "bb"], auth1)  # Pop is FIFO
        self.assertEqual(["c", "d"], auth2)
        self.assertEqual(["a", "b"], auth3)
        self.assertEqual(["a", "b"], auth4)

    def test_login_good_auth(self) -> None:
        # Given
        init_cookies = {'JSESSIONID': 'abc', '__appianCsrfToken': '123'}
        cookies = {'JSESSIONID': 'abc123',
                   '__appianCsrfToken': 'different cookie',
                   '__appianMultipartCsrfToken': 'these cookies'}
        self.custom_locust.set_response("/suite/", 200,
                                        '<html>A huge html blob</html>', cookies=init_cookies)
        self.custom_locust.set_response("/suite/auth?appian_environment=tempo", 200,
                                        '<html>A huge html blob</html>', cookies=cookies)

        self.task_set.appian.login(["", ""])
        self.assertEqual(cookies, self.task_set.appian.client.cookies)

    def test_login_bad_auth(self) -> None:
        # Given
        self.custom_locust.set_response("/suite/auth?appian_environment=tempo", 401,
                                        'The username/password entered is invalid')

        with self.assertRaisesRegex(BadCredentialsException, "Could not log in"):
            self.task_set.appian.login(["", ""])

    def test_login_bad_auth_bad_cookies(self) -> None:
        # Given
        cookies = {'JSESSIONID': 'abc', '__appianCsrfToken': '123'}
        self.custom_locust.set_response("/suite/", 200,
                                        '<html>A huge html blob</html>', cookies=cookies)
        self.custom_locust.set_response("/suite/auth?appian_environment=tempo", 200,
                                        '<html>A huge html blob</html>', cookies=cookies)

        with self.assertRaisesRegex(MissingCsrfTokenException, "Login unsuccessful, no multipart cookie found"):
            self.task_set.on_start()

    def test_instantiating_task_set(self) -> None:
        # Given
        ts = SampleAppianTaskSequence(self.custom_locust)

        # When
        task_name_1 = ts.get_next_task().__name__

        # Then
        self.assertEqual("first_task", task_name_1)

        # When called again
        task_name_2 = ts.get_next_task().__name__

        # Then the next task
        self.assertEqual("second_task", task_name_2)

        # When called the last time
        task_name_3 = ts.get_next_task().__name__

        # Then it wraps around
        self.assertEqual("first_task", task_name_3)

    def test_appian_client_on_its_own(self) -> None:
        # Given
        inner_client = MockClient()

        dir_path = os.path.dirname(os.path.realpath(__file__))
        actions = read_mock_file("actions_response.json")
        host = "https://my-fake-host.com"
        inner_client.set_response(
            f"{host}/suite/api/tempo/open-a-case/available-actions?ids=%5B%5D", 200, actions)
        appian_client = AppianClient(inner_client, "https://my-fake-host.com")

        # When
        client, resp = appian_client.login(["a", "1"])
        appian_client.actions.get_all()

        # Then
        self.assertEqual(200, resp.status_code)

    def test_procedurally_generate_credentials(self) -> None:
        # Given
        CONFIG = {"procedural_credentials_prefix": "employee",
                  "procedural_credentials_count": 3,
                  "procedural_credentials_password": "pass"}

        expected_credentials = [['employee1', 'pass'], ['employee2', 'pass'], ['employee3', 'pass']]
        # When
        procedurally_generate_credentials(CONFIG)

        # Then
        self.assertEqual(expected_credentials, CONFIG["credentials"])

    def test_procedurally_generate_credentials_keys_missing(self) -> None:
        # Given
        CONFIG = {"procedural_credentials_prefix": "employee",
                  "procedural_credentials_password": "pass"}

        # When
        with self.assertRaisesRegex(MissingConfigurationException, '["procedural_credentials_count"]'):
            procedurally_generate_credentials(CONFIG)

    def test_procedurally_generate_credentials_multiple_keys_missing(self) -> None:
        # Given
        CONFIG2 = {'unrelated': 'config'}

        # When
        with self.assertRaisesRegex(MissingConfigurationException, '["procedural_credentials_prefix", "procedural_credentials_count", "procedural_credentials_password"]'):
            procedurally_generate_credentials(CONFIG2)

    def test_setup_distributed_creds(self) -> None:
        # Given
        CONFIG = {"credentials": [['employee1', 'pass'], ['employee2', 'pass'], ['employee3', 'pass']]}
        os.environ["STY"] = "64331.locustdriver-2-0"
        expected_config = [['employee1', 'pass'], ['employee3', 'pass']]

        # When
        setup_distributed_creds(CONFIG)
        self.assertEqual(CONFIG["credentials"], expected_config)

    def test_setup_distributed_creds_2(self) -> None:
        # Given
        CONFIG = {"credentials": [['employee1', 'pass'], ['employee2', 'pass'], ['employee3', 'pass']]}
        os.environ["STY"] = "64331.locustdriver-2-1"
        expected_config = [['employee2', 'pass']]

        # When
        setup_distributed_creds(CONFIG)
        self.assertEqual(CONFIG["credentials"], expected_config)

    def test_setup_distributed_creds_fewer_credentials_than_workers(self) -> None:
        # Given
        CONFIG = {"credentials": [['employee1', 'pass']]}
        os.environ["STY"] = "64331.locustdriver-2-1"
        expected_config = [['employee1', 'pass']]

        # When
        setup_distributed_creds(CONFIG)
        self.assertEqual(CONFIG["credentials"], expected_config)

    def test_setup_distributed_creds_fails_missing_key(self) -> None:
        # Given
        CONFIG = {'unrelated': 'config'}

        # When
        with self.assertRaisesRegex(MissingConfigurationException, '["credentials"]'):
            setup_distributed_creds(CONFIG)


if __name__ == '__main__':
    unittest.main()

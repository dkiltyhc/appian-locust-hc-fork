import json
import unittest
from typing import Any
from unittest import mock

from appian_locust import AppianTaskSet, logger
from appian_locust.uiform import SailUiForm
from locust import Locust, TaskSet

from tests.mock_client import CustomLocust
from tests.mock_reader import read_mock_file

log = logger.getLogger(__name__)


class TestRecords(unittest.TestCase):
    record_types = read_mock_file("record_types_response.json")
    # Record Insance List for a specific RecordType
    records = read_mock_file("records_response.json")
    # Record Summary dashboard response for a specific Record Instance
    record_summary_view = read_mock_file("record_summary_view_response.json")
    record_instance_name = "Actions Page"

    def setUp(self) -> None:
        self.custom_locust = CustomLocust(Locust())
        parent_task_set = TaskSet(self.custom_locust)
        setattr(parent_task_set, "host", "")
        setattr(parent_task_set, "auth", ["", ""])
        self.task_set = AppianTaskSet(parent_task_set)
        self.task_set.host = ""

        # test_on_start_auth_success is covered here.
        self.custom_locust.set_response("auth?appian_environment=tempo", 200, '{}')
        if not hasattr(self.task_set, 'appian'):
            self.task_set.on_start()

        self.custom_locust.set_response("/suite/rest/a/applications/latest/app/records/view/all", 200,
                                        self.record_types)
        self.custom_locust.set_response("/suite/rest/a/sites/latest/D6JMim/pages/records/recordType/commit", 200,
                                        self.records)
        self.custom_locust.set_response("/suite/rest/a/applications/latest/legacy/tempo/records/type/commit/view/all", 200,
                                        self.records)
        self.custom_locust.set_response(
            "/suite/rest/a/sites/latest/D6JMim/page/records/record/lQB0K7YxC0UQ2Fhx4pmY1F49C_MjItD4hbtRdKDmOo6V3MOBxI47ipGa_bJKZf86CLtvOCp1cfX-sa2O9hp6WTKZpbGo5MxRaaTwMkcYMeDl8kN8Hg/view/summary",
            200,
            self.record_summary_view)

    def tearDown(self) -> None:
        self.task_set.on_stop()

    def test_records_get_all(self) -> None:
        all_records = self.task_set.appian.records.get_all()
        self.assertIsInstance(all_records, dict)

    def test_records_get_all_bad_response(self) -> None:

        # setting up bad response
        temp_record_types = self.record_types.replace(
            '"rel":"x-web-bookmark"', '"rel":"bad_x-web-bookmark_bad"'
        ).replace(
            '"#t":"CardLayout"', '"#t":"bad_CardLayout_bad"'
        )
        self.custom_locust.set_response("/suite/rest/a/applications/latest/app/records/view/all", 200,
                                        temp_record_types)
        with(self.assertRaisesRegex(Exception, "Unexpected response on Get call of All Records")):
            self.task_set.appian.records.get_all()

    def test_records_get_corrupt_records(self) -> None:
        # setting up bad response
        corrupt_records = self.records.replace('"_recordRef": "lQB0K7YxC0UQ2Fhx4pmY1F49C_MjItD4hbtRdKDmOo6V3MOBxI47ipGa_bJKZf86CLtvOCp1cfX-sa2O9hu7mTKKv82PEWF9q1lBcroZD_VQpwcQDs"',
                                               '"corrupt_recordRef": "lQB0K7YxC0UQ2Fhx4pmY1F49C_MjItD4hbtRdKDmOo6V3MOBxI47ipGa_bJKZf86CLtvOCp1cfX-sa2O9hu7mTKKv82PEWF9q1lBcroZD_VQpwcQDs"')
        self.custom_locust.set_response("/suite/rest/a/sites/latest/D6JMim/pages/records/recordType/commit", 200,
                                        corrupt_records)

        all_records = self.task_set.appian.records.get_all()
        self.assertTrue("ERROR::1" in str(all_records))
        self.assertTrue(self.task_set.appian.records._errors == 1)

    def test_records_get_all_mobile(self) -> None:
        all_records = self.task_set.appian.records.get_all_mobile()
        self.assertIsInstance(all_records, dict)

    def test_records_get_by_type_mobile(self) -> None:
        # Given
        record_type = 'Commits'
        self.task_set.appian.records.get_all_record_types()

        # When
        all_records = self.task_set.appian.records.get_all_records_of_record_type_mobile(record_type)

        # Then
        self.assertIsInstance(all_records, dict)

    def test_records_fetch_record_instance(self) -> None:
        record = self.task_set.appian.records.fetch_record_instance(
            "Commits", self.record_instance_name, False)
        self.assertIsInstance(record, dict)

    def test_records_fetch_record_instance_no_record_type(self) -> None:
        with self.assertRaisesRegex(Exception,
                                    "There is no record type with name .* in the system under test"):
            self.task_set.appian.records.fetch_record_instance("something else 1", self.record_instance_name, False)

    def test_records_fetch_record_instance_missing(self) -> None:
        with self.assertRaisesRegex(Exception,
                                    "There is no record with name .* found in record type .*"):
            self.task_set.appian.records.fetch_record_instance("Commits", "something else", False)

    def test_records_fetch_record_type(self) -> None:
        self.task_set.appian.records.get_all()
        output = self.task_set.appian.records.fetch_record_type("Commits")
        self.assertIsInstance(output, dict)

    def test_records_fetch_record_type_recaching(self) -> None:
        self.task_set.appian.records._record_types = dict()  # Resetting the cache.
        output = self.task_set.appian.records.fetch_record_type("Commits")
        self.assertIsInstance(output, dict)

    def test_records_fetch_record_type_missing_record_type(self) -> None:
        with self.assertRaisesRegex(Exception,
                                    "There is no record type with name .* in the system under test"):
            self.task_set.appian.records.fetch_record_type("something else")

    def test_records_visit(self) -> None:
        output_json, output_uri = self.task_set.appian.records.visit_record_instance(
            "Commits", self.record_instance_name, exact_match=False)
        self.assertIsInstance(output_json, dict)
        self.assertTrue("summary" in output_uri)

    def test_records_visit_random_success(self) -> None:
        self.custom_locust.set_default_response(200, self.record_summary_view)
        output_json, output_uri = self.task_set.appian.records.visit_record_instance()
        self.assertIsInstance(output_json, dict)
        self.assertTrue("summary" in output_uri)

    def test_records_visit_random_of_selected_record_type_success(self) -> None:
        self.custom_locust.set_default_response(200, self.record_summary_view)
        output_json, output_uri = self.task_set.appian.records.visit_record_instance(record_type="Commits")
        self.assertIsInstance(output_json, dict)
        self.assertTrue("summary" in output_uri)

    def test_records_visit_random_no_record_type_failure(self) -> None:
        with self.assertRaisesRegex(Exception,
                                    "If record_name parameter is specified, record_type must also be included"):
            self.task_set.appian.records.visit_record_instance(record_name=self.record_instance_name, exact_match=False)

    def test_records_visit_with_urlstub(self) -> None:
        output_json, output_uri = self.task_set.appian.records.visit_record_instance(
            "Commits", self.record_instance_name, "summary", exact_match=False)
        self.assertIsInstance(output_json, dict)
        self.assertTrue("summary" in output_uri)

    def test_record_types_visit(self) -> None:
        output_json, output_uri = self.task_set.appian.records.visit_record_type(
            "Commits", exact_match=False)
        self.assertIsInstance(output_json, dict)
        self.assertTrue("commit" in output_uri)

    def test_record_type_visit_random_success(self) -> None:
        self.custom_locust.set_default_response(200, self.records)
        output_json, output_uri = self.task_set.appian.records.visit_record_type()
        self.assertIsInstance(output_json, dict)
        self.assertEqual(output_json.get("#t"), "UiConfig")
        self.assertTrue("commit" in output_uri)

    def test_record_type_visit_failure(self) -> None:
        with self.assertRaises(Exception) as e:
            self.task_set.appian.records.visit_record_type(record_type="fake type")

    @unittest.mock.patch('appian_locust.records_helper.find_component_by_attribute_in_dict', return_value={'children': [json.dumps({"a": "b"})]})
    def test_records_form_example_success(self, find_component_by_attribute_in_dict_function: Any) -> None:
        sail_form = self.task_set.appian.records.visit_record_instance_and_get_form(
            "Commits",
            self.record_instance_name,
            view_url_stub="summary",
            exact_match=False
        )
        self.assertTrue(isinstance(sail_form, SailUiForm))
        self.assertEqual(sail_form.get_response(), {"a": "b"})

    def test_records_form_incorrect_name(self) -> None:
        record_name = "Fake Record"
        record_type = "Commits"
        exact_match = False
        with self.assertRaises(Exception) as context:
            self.task_set.appian.records.visit_record_instance_and_get_form(
                record_type,
                record_name,
                view_url_stub="summary",
                exact_match=exact_match
            )
        self.assertEqual(
            context.exception.args[0], f"There is no record with name {record_name} found in record type {record_type} (Exact match = {exact_match})")

    def test_records_form_incorrect_type(self) -> None:
        exact_match = False
        with self.assertRaises(Exception) as context:
            self.task_set.appian.records.visit_record_instance_and_get_form(
                "Fake Type",
                self.record_instance_name,
                view_url_stub="summary",
                exact_match=exact_match
            )
        self.assertEqual(
            context.exception.args[0], f"There is no record type with name Fake Type in the system under test (Exact match = {exact_match})")

    @unittest.mock.patch('appian_locust.records_helper.find_component_by_attribute_in_dict', return_value={'children': None})
    def test_records_form_no_embedded_summary(self, find_component_by_attribute_in_dict_function: Any) -> None:
        with self.assertRaises(Exception) as context:
            self.task_set.appian.records.visit_record_instance_and_get_form(
                record_type="Commits",
                record_name=self.record_instance_name,
                view_url_stub="summary",
                exact_match=False)
        self.assertEqual(
            context.exception.args[0],
            "Parser was not able to find embedded SAIL code within JSON response for the requested Record Instance.")

    def test_record_types_form_example_success(self) -> None:
        sail_form = self.task_set.appian.records.visit_record_type_and_get_form(
            "Commits",
            exact_match=False
        )
        self.assertTrue(isinstance(sail_form, SailUiForm))

    def test_record_type_random_form_example_success(self) -> None:
        sail_form = self.task_set.appian.records.visit_record_type_and_get_form(exact_match=False)
        self.assertTrue(isinstance(sail_form, SailUiForm))

    def test_record_type_form_incorrect_type(self) -> None:
        record_type = "Fake Type"
        exact_match = True
        with self.assertRaises(Exception) as context:
            self.task_set.appian.records.visit_record_type_and_get_form(
                record_type,
                exact_match
            )
        self.assertEqual(
            context.exception.args[0], f"There is no record type with name {record_type} in the system under test")

    def test_get_random_record(self) -> None:
        self.task_set.appian.records._record_types = dict()
        self.task_set.appian.records._records = dict()
        record_type, record_name = self.task_set.appian.records._get_random_record_instance()
        self.assertEqual(record_type, "Commits")
        self.assertIn(record_name, list(self.task_set.appian.records._records[record_type].keys()))

    def test_get_random_record_get_all(self) -> None:
        mock_get_all = mock.Mock()
        setattr(self.task_set.appian.records, 'get_all', mock_get_all)
        with self.assertRaises(Exception):
            self.task_set.appian.records._get_random_record_instance()
            mock_get_all.assert_called_once()

    def test_get_record_instance_feed_Response(self) -> None:
        sail_form = self.task_set.appian.records.visit_record_instance_and_get_feed_form(
            "Commits",
            self.record_instance_name,
            exact_match=False)

        self.assertTrue(isinstance(sail_form, SailUiForm))
        self.assertEqual(sail_form.state.get("feed", {}).get("title", ""), self.record_instance_name)


if __name__ == '__main__':
    unittest.main()

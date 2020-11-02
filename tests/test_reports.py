from locust import TaskSet, Locust
from .mock_client import CustomLocust
from .mock_reader import read_mock_file
from appian_locust import AppianTaskSet, SailUiForm
import unittest


class TestReports(unittest.TestCase):
    reports = read_mock_file("reports_response.json")

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

        self.custom_locust.set_response("/suite/rest/a/uicontainer/latest/reports", 200, self.reports)

    def tearDown(self) -> None:
        self.task_set.on_stop()

    def test_reports_get_all(self) -> None:
        all_reports = self.task_set.appian.reports.get_all()
        self.assertIsInstance(all_reports, dict)

    def test_reports_get(self) -> None:
        reports = self.task_set.appian.reports.get_report(
            "RTE Basic Test Report::qdjDPA")
        self.assertIsInstance(reports, dict)

    def test_reports_get_corrupt_report(self) -> None:
        corrupt_reports = self.reports.replace('"title": "!!SAIL test charts"', '"corrupt_title": "!!SAIL test charts"')
        self.custom_locust.set_response("/suite/rest/a/uicontainer/latest/reports", 200, corrupt_reports)
        all_reports = self.task_set.appian.reports.get_all()
        self.assertTrue("ERROR::1" in str(all_reports))
        self.assertEqual(1, self.task_set.appian.reports._errors)

    def test_reports_zero_reports(self) -> None:
        corrupt_reports = self.reports.replace('"entries"', '"nonexistent_entries"')
        self.custom_locust.set_response("/suite/rest/a/uicontainer/latest/reports", 200, corrupt_reports)
        all_reports = self.task_set.appian.reports.get_all()
        self.assertTrue(all_reports == {})

    def test_reports_get_missing_report(self) -> None:
        with self.assertRaisesRegex(Exception, "There is no report with name .* in the system under test.*"):
            self.task_set.appian.reports.get_report("some random word")

    def test_reports_visit(self) -> None:
        self.custom_locust.set_response("/suite/rest/a/sites/latest/D6JMim/pages/reports/report/qdjDPA/reportlink",
                                        200, "{}")
        output = self.task_set.appian.reports.visit("RTE Basic Test Report::qdjDPA")
        self.assertEqual(output, dict())

    def test_reports_form_example_success(self) -> None:
        self.custom_locust.set_response("/suite/rest/a/sites/latest/D6JMim/pages/reports/report/qdjDPA/reportlink",
                                        200, '{"context":123, "uuid":123}')

        sail_form = self.task_set.appian.reports.visit_and_get_form(
            "RTE Basic Test Report", False)
        self.assertTrue(isinstance(sail_form, SailUiForm))

    def test_reports_form_example_failure(self) -> None:
        self.custom_locust.set_response("/suite/rest/a/sites/latest/D6JMim/pages/reports/report/qdjDPA/reportlink",
                                        200, '{"context":123, "uuid":123}')

        report_name = "Fake Report"
        exact_match = False
        with self.assertRaises(Exception) as context:
            self.task_set.appian.reports.visit_and_get_form(
                report_name, exact_match)
        self.assertEqual(
            context.exception.args[0], f"There is no report with name {report_name} in the system under test (Exact match = {exact_match})")


if __name__ == '__main__':
    unittest.main()

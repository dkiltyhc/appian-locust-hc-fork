import unittest
import json

from requests.exceptions import HTTPError

from appian_locust import AppianTaskSet, SailUiForm
from locust import User, TaskSet

from .mock_client import CustomLocust
from .mock_reader import read_mock_file
from typing import List
from appian_locust.helper import find_component_by_attribute_in_dict
from appian_locust.helper import ENV


class TestSailUiForm(unittest.TestCase):

    reports = read_mock_file("reports_response.json")

    def setUp(self) -> None:
        self.custom_locust = CustomLocust(User(ENV))
        parent_task_set = TaskSet(self.custom_locust)
        setattr(parent_task_set, "host", "")
        setattr(parent_task_set, "auth", ["", ""])
        self.task_set = AppianTaskSet(parent_task_set)
        self.task_set.host = ""

        # test_on_start_auth_success is covered here.
        self.custom_locust.set_response("auth?appian_environment=tempo", 200, '{}')
        self.task_set.on_start()

        self.custom_locust.set_response("/suite/rest/a/uicontainer/latest/reports", 200, self.reports)
        ENV.stats.clear_all()

    def test_reports_form_example_fail(self) -> None:
        self.custom_locust.set_response("/suite/rest/a/sites/latest/D6JMim/pages/reports/report/nXLBqg/reportlink",
                                        500, '{}')
        with self.assertRaises(HTTPError):
            sail_form = self.task_set.appian.reports.visit_and_get_form("Batch Query Report", False)

    def test_reports_form_modify_grid(self) -> None:
        form_label = 'Top Sales Reps by Total Sales'
        report_form = read_mock_file("report_with_rep_sales_grid.json")
        self.custom_locust.set_response("/suite/rest/a/sites/latest/D6JMim/pages/reports/report/nXLBqg/reportlink",
                                        200, report_form)
        sail_form = self.task_set.appian.reports.visit_and_get_form("Batch Query Report", False)
        self.custom_locust.set_response("/suite/rest/a/sites/latest/D6JMim/pages/reports/report/yS9bXA/reportlink",
                                        200, report_form)

        keyWords: List[dict] = [{'label': form_label}, {'index': 0}]
        for i in range(len(keyWords)):
            keyword_args: dict = keyWords[i]
            sail_form.move_to_beginning_of_paging_grid(**keyword_args)
            sail_form.move_to_end_of_paging_grid(**keyword_args)
            sail_form.move_to_left_in_paging_grid(**keyword_args)
            sail_form.move_to_right_in_paging_grid(**keyword_args)
            keyword_args['field_name'] = 'Total'
            sail_form.sort_paging_grid(**keyword_args)

    def test_reports_form_modify_grid_errors(self) -> None:
        form_label = 'Top Sales Reps by Total Sales'
        report_form = read_mock_file("report_with_rep_sales_grid.json")
        self.custom_locust.set_response("/suite/rest/a/sites/latest/D6JMim/pages/reports/report/nXLBqg/reportlink",
                                        200, report_form)
        sail_form = self.task_set.appian.reports.visit_and_get_form("Batch Query Report", False)
        with self.assertRaisesRegex(Exception, "Grid with label 'dummy_label'"):
            sail_form.move_to_beginning_of_paging_grid(label='dummy_label')
        with self.assertRaisesRegex(Exception, "Index 5 out of range"):
            sail_form.move_to_left_in_paging_grid(index=5)
        with self.assertRaisesRegex(Exception, "Cannot sort, field 'Abc' not found"):
            sail_form.sort_paging_grid(index=0, field_name='Abc')
        with self.assertRaisesRegex(Exception, "Field to sort cannot be blank"):
            sail_form.sort_paging_grid(index=0)
        self.assertEqual(4, len(ENV.stats.errors))

    def test_datatype_caching(self) -> None:
        body_with_types = read_mock_file("page_resp.json")
        self.custom_locust.set_response("/suite/rest/a/sites/latest/D6JMim/pages/reports/report/nXLBqg/reportlink",
                                        200, body_with_types)
        sail_form = self.task_set.appian.reports.visit_and_get_form("Batch Query Report", False)
        self.assertEqual(len(self.task_set.appian.interactor.datatype_cache._cached_datatype), 105)
        sail_form = self.task_set.appian.reports.visit_and_get_form("Batch Query Report", False)
        self.assertEqual(len(self.task_set.appian.interactor.datatype_cache._cached_datatype), 105)

    def test_deployments_click_tab(self) -> None:
        design_landing_page_response = read_mock_file("design_landing_page.json")
        deployment_tab_response = read_mock_file("design_deployments_ui.json")
        deployment_outgoing_tab_response = read_mock_file("design_deployments_outgoing_tab.json")

        self.custom_locust.set_response("/suite/rest/a/applications/latest/app/design",
                                        200, design_landing_page_response)
        design_sail_form = self.task_set.appian.design.visit()

        self.custom_locust.set_response("/suite/rest/a/applications/latest/app/design",
                                        200, deployment_tab_response)
        deployments_sail_form = design_sail_form.click("Deployments")

        self.custom_locust.set_response("/suite/rest/a/applications/latest/app/design/deployments",
                                        200, deployment_outgoing_tab_response)
        outgoing_tab_form = deployments_sail_form.get_latest_form().click_tab_by_label("Outgoing", "deployment-secondary-tabs")

        component = find_component_by_attribute_in_dict("label", "OneApp", outgoing_tab_form.latest_state)
        self.assertEqual("OneApp", component.get('label'))

    def test_deployments_click_tab_exception(self) -> None:
        deployment_tab_response = read_mock_file("design_deployments_ui.json")
        design_landing_page_response = read_mock_file("design_landing_page.json")
        self.custom_locust.set_response("/suite/rest/a/applications/latest/app/design",
                                        200, design_landing_page_response)
        design_sail_form = self.task_set.appian.design.visit()

        self.custom_locust.set_response("/suite/rest/a/applications/latest/app/design",
                                        200, deployment_tab_response)
        deployments_sail_form = design_sail_form.click("Deployments")
        with self.assertRaisesRegex(Exception, "Cannot click a tab with label: 'DoesNotExistLabel' inside the TabButtonGroup component"):
            outgoing_tab_form = deployments_sail_form.get_latest_form().click_tab_by_label("DoesNotExistLabel", "deployment-secondary-tabs")

    def test_picker_widget_interaction(self) -> None:
        sail_ui_actions_cmf = json.loads(read_mock_file("sail_ui_actions_cmf.json"))
        picker_widget_suggestions = read_mock_file("picker_widget_suggestions.json")
        picker_widget_selected = read_mock_file("picker_widget_selected.json")

        self.custom_locust.enqueue_response(200, picker_widget_suggestions)
        self.custom_locust.enqueue_response(200, picker_widget_selected)

        sail_form = SailUiForm(self.task_set.appian.interactor, sail_ui_actions_cmf, "/suite/rest/a/model/latest/8/form")

        label = '1. Select a Customer'
        value = 'Antilles Transport'
        resp = sail_form.fill_picker_field(label, value)

    def test_picker_widget_no_suggestions(self) -> None:
        sail_ui_actions_cmf = json.loads(read_mock_file("sail_ui_actions_cmf.json"))
        picker_widget_suggestions = read_mock_file("picker_widget_no_suggestions.json")

        self.custom_locust.enqueue_response(200, picker_widget_suggestions)
        sail_form = SailUiForm(self.task_set.appian.interactor, sail_ui_actions_cmf, "/suite/rest/a/model/latest/8/form")

        label = '1. Select a Customer'
        value = 'You will not find me'
        with self.assertRaises(Exception):
            resp = sail_form.fill_picker_field(label, value)

    def test_upload_document_invalid_component(self) -> None:
        with self.assertRaisesRegex(Exception, 'Provided component was not a FileUploadWidget'):
            label = 'my_label'
            ui = {
                'contents': [

                    {
                        "contents": {
                            "label": label,
                            "#t": "Some other thing"
                        },
                        "label": label,
                        "labelPosition": "ABOVE",
                        "instructions": "",
                        "instructionsPosition": "",
                        "helpTooltip": "Upload an application or a multi-patch package",
                        "requiredStyle": "",
                        "skinName": "",
                        "marginBelow": "",
                        "accessibilityText": "",
                        "#t": "FieldLayout"
                    },
                ]
            }
            sail_form = SailUiForm(self.task_set.appian.interactor, ui, "/suite/rest/a/model/latest/8/form")
            sail_form.upload_document_to_upload_field(label, 'fake_file')

    def test_upload_document_missing_file(self) -> None:
        file = 'fake_file'
        with self.assertRaisesRegex(Exception, f"No such file or directory: '{file}'"):
            label = 'my_label'
            ui = {
                'contents': [

                    {
                        "label": label,
                        "labelPosition": "ABOVE",
                        "instructions": "",
                        "instructionsPosition": "",
                        "helpTooltip": "Upload an application or a multi-patch package",
                        "requiredStyle": "",
                        "skinName": "",
                        "marginBelow": "",
                        "accessibilityText": "",
                        "#t": "FileUploadWidget"
                    },
                ]
            }
            sail_form = SailUiForm(self.task_set.appian.interactor, ui, "/suite/rest/a/model/latest/8/form")
            sail_form.upload_document_to_upload_field(label, file)


if __name__ == '__main__':
    unittest.main()

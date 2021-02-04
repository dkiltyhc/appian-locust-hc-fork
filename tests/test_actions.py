from locust import TaskSet, Locust
from .mock_client import CustomLocust
from .mock_reader import read_mock_file
from appian_locust import AppianTaskSet, SailUiForm
from appian_locust.uiform import (ComponentNotFoundException,
                                  ChoiceNotFoundException, InvalidComponentException)

import os
import unittest
from unittest.mock import patch, MagicMock
from typing import Optional


class TestActions(unittest.TestCase):

    actions = read_mock_file("actions_response.json")

    action_under_test = "Create a Case::koBOPgHGLIgHRQzrdseY6-wW_trk0FY-87TIog3LDZ9dbSn9dYtlSaOQlWaz7PcZgV5FWdIgYk8QRlv1ARbE4czZL_8fj4ckCLzqA"

    def setUp(self) -> None:
        self.custom_locust = CustomLocust(Locust())
        parent_task_set = TaskSet(self.custom_locust)
        setattr(parent_task_set, "host", "")
        setattr(parent_task_set, "auth", ["", ""])
        self.task_set = AppianTaskSet(parent_task_set)
        self.task_set.host = ""

        # test_on_start_auth_success is covered here.
        self.custom_locust.set_response(
            "auth?appian_environment=tempo", 200, '{}')
        self.task_set.on_start()

        self.custom_locust.set_response(
            "/suite/api/tempo/open-a-case/available-actions?ids=%5B%5D", 200, self.actions)

    def tearDown(self) -> None:
        self.task_set.on_stop()

    def test_actions_get_all(self) -> None:
        all_actions = self.task_set.appian.actions.get_all()
        self.assertTrue(len(list(all_actions.keys())) > 0)

    def test_actions_get(self) -> None:
        action = self.task_set.appian.actions.get_action(
            self.action_under_test)
        self.assertEqual(action['displayLabel'], 'Create a Case')

    def test_actions_get_corrupt_action(self) -> None:
        corrupt_actions = self.actions.replace('"opaqueId": "koBOPgHGLIgHRQzrdseZ66wChtz5aQqM_RBTDeSBi9lWr4b18XPJqrikBSQYzzp8_e2Wgw0ku-apJjK94StAV1R3DU5zipwSXfCTA"',
                                               '"corrupt_opaqueId": "koBOPgHGLIgHRQzrdseZ66wChtz5aQqM_RBTDeSBi9lWr4b18XPJqrikBSQYzzp8_e2Wgw0ku-apJjK94StAV1R3DU5zipwSXfCTA"')
        self.custom_locust.set_response("/suite/api/tempo/open-a-case/available-actions?ids=%5B%5D", 200, corrupt_actions)
        all_actions = self.task_set.appian.actions.get_all()
        self.assertTrue("ERROR::1" in str(all_actions))
        self.assertTrue(self.task_set.appian.actions._errors == 1)

    def test_actions_zero_actions(self) -> None:
        corrupt_actions = self.actions.replace('"actions"', '"nonexistent_actions"')
        self.custom_locust.set_response("/suite/api/tempo/open-a-case/available-actions?ids=%5B%5D", 200, corrupt_actions)
        all_actions = self.task_set.appian.actions.get_all()
        self.assertTrue(all_actions == {})

    def test_actions_get_partial_match(self) -> None:
        action = self.task_set.appian.actions.get_action("Create a Case", False)
        self.assertEqual(action['displayLabel'], 'Create a Case')

    def test_actions_get_multiple_matches(self) -> None:
        self.task_set.appian.actions._actions = dict()  # Resetting the cache.
        action = self.task_set.appian.actions.get_action("Create a C", False)
        self.assertTrue("Create a C" in action['displayLabel'])

    def test_actions_get_missing_action(self) -> None:
        with self.assertRaisesRegex(Exception, "There is no action with name .* in the system under test.*"):
            self.task_set.appian.actions.get_action("Create a Case", exact_match=True)

    def setup_action_response_no_ui(self) -> None:
        action = self.task_set.appian.actions.get_action("Create a Case", False)
        self.custom_locust.set_response(action['formHref'], 200, "{}")

    def setup_action_response_with_ui(self, file_name: str = "form_content_response.json") -> None:
        action = self.task_set.appian.actions.get_action("Create a Case", False)
        resp_json = read_mock_file(file_name)
        self.custom_locust.set_response(action['formHref'], 200, resp_json)

    def test_actions_visit(self) -> None:
        self.setup_action_response_no_ui()
        action = self.task_set.appian.actions.visit("Create a Case", False)
        self.assertIsInstance(action, dict)

    def test_actions_start(self) -> None:
        self.setup_action_response_no_ui()
        self.task_set.appian.actions.start_action(
            self.action_under_test)

    def test_actions_start_skip_design_call(self) -> None:
        self.task_set.appian.actions.start_action(
            self.action_under_test,
            True)

    def test_actions_form_example_success(self) -> None:
        # output of get_page of a form (SAIL)
        self.setup_action_response_with_ui()
        self.custom_locust.set_response(
            '/suite/rest/a/model/latest/228/form', 200, '{"context":"12345","ui": {"#t": "UiComponentsDelta", "modifiedComponents":[]}}')
        sail_form: SailUiForm = self.task_set.appian.actions.visit_and_get_form(
            "Create a Case", False)

        label = 'Title'
        value = "Look at me, I am filling out a form"
        button_label = 'Submit'
        latest_form = sail_form.fill_text_field(label, value).click(button_label)

        resp = latest_form.get_response()
        self.assertEqual("12345", resp['context'])

    def test_actions_form_example_activity_chained(self) -> None:
        action = self.task_set.appian.actions.get_action("Create a Case", False)
        resp_json = read_mock_file("form_content_response.json")

        self.custom_locust.set_response(action['formHref'], 200, '{"mobileEnabled": "false", "empty": "true", "formType": "START_FORM"}')
        self.custom_locust.set_response(action['initiateActionHref'], 200, resp_json)
        self.custom_locust.set_response(
            '/suite/rest/a/model/latest/228/form', 200, '{"context":"12345","ui": {"#t": "UiComponentsDelta", "modifiedComponents":[]}}')
        sail_form: SailUiForm = self.task_set.appian.actions.visit_and_get_form("Create a Case")

        label = 'Title'
        value = "Look at me, I am filling out a form"
        button_label = 'Submit'
        latest_form = sail_form.fill_text_field(label, value).click(button_label)

        resp = latest_form.get_response()
        self.assertEqual("12345", resp['context'])

    def test_actions_form_example_missing_field(self) -> None:
        self.setup_action_response_with_ui()
        sail_form: SailUiForm = self.task_set.appian.actions.visit_and_get_form(
            "Create a Case", False)

        value = "Look at me, I am filling out a form"
        label = "missingText"
        with self.assertRaises(ComponentNotFoundException) as context:
            sail_form.fill_text_field(label, value)
        self.assertEqual(
            context.exception.args[0], f"Could not find the component with label '{label}' in the provided form")

        button_label = 'press me'
        with self.assertRaises(ComponentNotFoundException) as context:
            sail_form.click(button_label)
        self.assertEqual(
            context.exception.args[0], f"Could not find the component with label '{button_label}' in the provided form")

    def test_actions_form_example_bad_response(self) -> None:
        self.setup_action_response_with_ui()
        sail_form: SailUiForm = self.task_set.appian.actions.visit_and_get_form(
            "Create a Case", False)

        self.custom_locust.set_response(
            '/suite/rest/a/model/latest/228/form', 200, 'null')

        value = "Look at me, I am filling out a form"
        label = "Title"
        with self.assertRaises(Exception) as context:
            sail_form.fill_text_field(label, value)
        self.assertEqual(
            context.exception.args[0], f"No response returned when trying to update field with label '{label}'")

        button_label = 'Submit'
        with self.assertRaises(Exception) as context:
            sail_form.click(button_label)
        self.assertEqual(
            context.exception.args[0], f"No response returned when trying to click button with label '{button_label}'")

    def test_actions_form_dropdown_errors(self) -> None:
        self.setup_action_response_with_ui('dropdown_test_ui.json')

        sail_form: SailUiForm = self.task_set.appian.actions.visit_and_get_form(
            "Create a Case", False)

        dropdown_label = "missing dropdown"
        with self.assertRaises(ComponentNotFoundException) as context:
            sail_form.select_dropdown_item(dropdown_label, 'some choice')
        self.assertEqual(
            context.exception.args[0], f"Could not find the component with label '{dropdown_label}' in the provided form")

        dropdown_label = "Name"
        with self.assertRaises(InvalidComponentException):
            sail_form.select_dropdown_item(dropdown_label, 'some choice')

        dropdown_label = "Customer Type"
        with self.assertRaises(ChoiceNotFoundException):
            sail_form.select_dropdown_item(dropdown_label, 'some missing choice')

    @patch('appian_locust.SailUiForm._get_update_url_for_reeval', return_value="/mocked/re-eval/url")
    @patch('appian_locust.uiform._Interactor.send_dropdown_update')
    def test_actions_form_dropdown_success(self, mock_send_dropdown_update: MagicMock,
                                           mock_get_update_url_for_reeval: MagicMock) -> None:
        self.setup_action_response_with_ui('dropdown_test_ui.json')

        sail_form: SailUiForm = self.task_set.appian.actions.visit_and_get_form(
            "Create a Case", False)
        initial_state = sail_form.state

        dropdown_label = "Customer Type"
        sail_form.select_dropdown_item(dropdown_label, 'Buy Side Asset Manager')

        mock_get_update_url_for_reeval.assert_called_once_with(initial_state)
        mock_send_dropdown_update.assert_called_once()
        args, kwargs = mock_send_dropdown_update.call_args
        self.assertEqual(args[0], "/mocked/re-eval/url")
        self.assertNotEqual(sail_form.state, initial_state)

    @patch('appian_locust.uiform.find_component_by_attribute_in_dict')
    @patch('appian_locust.uiform._Interactor.select_radio_button')
    def test_actions_form_radio_button_by_label_success(self, mock_select_radio_button: MagicMock,
                                                        mock_find_component_by_label: MagicMock) -> None:
        self.setup_action_response_with_ui('dropdown_test_ui.json')

        sail_form: SailUiForm = self.task_set.appian.actions.visit_and_get_form(
            "Create a Case", False)
        state1 = sail_form.state

        button_label = "test-radio-button"
        sail_form.select_radio_button_by_test_label(button_label, 1)

        button_label = "Qualified Institutional Buyer"
        sail_form.select_radio_button_by_label(button_label, 1)

        args, kwargs = mock_find_component_by_label.call_args_list[0]
        self.assertEqual('testLabel', args[0])

        args_next_call, kwargs_next_call = mock_find_component_by_label.call_args_list[1]
        self.assertEqual('label', args_next_call[0])
        self.assertEqual(2, len(mock_select_radio_button.call_args_list))

    def test_actions_form_radio_button_by_label_error(self) -> None:
        self.setup_action_response_with_ui('dropdown_test_ui.json')

        sail_form: SailUiForm = self.task_set.appian.actions.visit_and_get_form(
            "Create a Case", False)

        button_label = "missing button"
        with self.assertRaises(ComponentNotFoundException) as context:
            sail_form.select_radio_button_by_test_label(button_label, 1)
        self.assertEqual(
            context.exception.args[0], f"Could not find the component with label '{button_label}' in the provided form")

        with self.assertRaises(ComponentNotFoundException) as context:
            sail_form.select_radio_button_by_label(button_label, 1)
        self.assertEqual(
            context.exception.args[0], f"Could not find the component with label '{button_label}' in the provided form")

    @patch('appian_locust.uiform.find_component_by_index_in_dict')
    @patch('appian_locust.uiform._Interactor.select_radio_button')
    def test_actions_form_radio_button_by_index_success(self, mock_select_radio_button: MagicMock,
                                                        mock_find_component_by_index: MagicMock) -> None:
        self.setup_action_response_with_ui('dropdown_test_ui.json')
        sail_form: SailUiForm = self.task_set.appian.actions.visit_and_get_form(
            "Create a Case", False)
        initial_state = sail_form.state
        button_index = 1
        sail_form.select_radio_button_by_index(button_index, 1)

        mock_select_radio_button.assert_called_once()
        mock_find_component_by_index.assert_called_with('RadioButtonField', button_index, initial_state)
        self.assertNotEqual(sail_form.state, initial_state)

    def test_actions_form_radio_button_by_index_error(self) -> None:
        self.setup_action_response_with_ui('dropdown_test_ui.json')

        sail_form: SailUiForm = self.task_set.appian.actions.visit_and_get_form(
            "Create a Case", False)

        index_too_low = -1
        with self.assertRaises(Exception) as context:
            sail_form.select_radio_button_by_index(index_too_low, 1)
        self.assertEqual(
            context.exception.args[0], f"Invalid index: '{index_too_low}'.  Please enter a positive number")

        index_too_high = 4
        with self.assertRaises(Exception) as context:
            sail_form.select_radio_button_by_index(index_too_high, 1)
        self.assertEqual(
            context.exception.args[0],
            f"Bad index: only '3' components of type 'RadioButtonField' found on page, requested '{index_too_high}'"
        )

        index_invalid = "bad index"
        with self.assertRaises(Exception) as context:
            sail_form.select_radio_button_by_index(index_invalid, 1)
        self.assertEqual(
            context.exception.args[0], f"Invalid index: '{index_invalid}'.  Please enter a positive number")


if __name__ == '__main__':
    unittest.main()

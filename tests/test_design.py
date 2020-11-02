from locust import TaskSet, Locust
from appian_locust.helper import ENV
from .mock_client import CustomLocust
from .mock_reader import read_mock_file
from appian_locust import AppianTaskSet
from appian_locust.uiform import (SailUiForm)
import unittest

integration_url = ""
auth = ["", ""]


class TestDesign(unittest.TestCase):
    def setUp(self) -> None:
        self.is_integration_mode = True if integration_url else False
        self.custom_locust = CustomLocust(
            Locust(), integration_url=integration_url, record_mode=self.is_integration_mode)
        parent_task_set = TaskSet(self.custom_locust)
        setattr(parent_task_set, "host", integration_url)
        setattr(parent_task_set, "auth", auth)
        self.task_set = AppianTaskSet(parent_task_set)

        # test_on_start_auth_success is covered here.
        if not self.is_integration_mode:
            self.custom_locust.set_response(
                "auth?appian_environment=tempo", 200, '{}')
        self.task_set.on_start()

    def test_visit(self) -> None:
        self.custom_locust.set_response(
            "/suite/rest/a/applications/latest/app/design", 200, read_mock_file("design_landing_page.json"))
        ENV.stats.clear_all()
        sail_form = self.task_set.appian.design.visit()
        self.assertEqual(type(sail_form), SailUiForm)
        self.assertEqual(0, len(ENV.stats.errors))

    def test_visit_app_and_deploy_app(self) -> None:
        app_id = "AADkMByLgAAY4-jvkOjvkAAAfXQ"
        if not self.is_integration_mode:
            next_button_modal = read_mock_file("design_next_button_modal.json")
            landing_page = read_mock_file("design_app_landing_page.json")
            self.custom_locust.enqueue_response(200, landing_page)
            self.custom_locust.enqueue_response(200, next_button_modal)
            self.custom_locust.enqueue_response(200, next_button_modal)
            self.custom_locust.enqueue_response(200, next_button_modal)
            self.custom_locust.enqueue_response(200, next_button_modal)
            self.custom_locust.enqueue_response(200, next_button_modal)
            self.custom_locust.enqueue_response(
                200, read_mock_file("design_deploy_button_modal.json"))
            self.custom_locust.enqueue_response(200, landing_page)
        ENV.stats.clear_all()
        sail_form = self.task_set.appian.design.visit_app(app_id)
        self.assertEqual(type(sail_form), SailUiForm)
        self.assertEqual(0, len(ENV.stats.errors))
        modal = sail_form.click_button('Compare and Deploy').get_latest_form().click('Next')\
            .get_latest_form().click('Select Target Environment', is_test_label=True)\
            .get_latest_form().click('Next')\
            .get_latest_form().click('Next')\
            .get_latest_form().click('Next')\
            .get_latest_form().click('Deploy')

    def test_visit_object(self) -> None:
        object_opaque_id = 'lABD1iTIu_lxy_3T_90Is2fs63uh52xESYi6-fun7FBWshlrBQ0EptlFUdGyIRzSSluPyVdvOhvGgL6aBlnjlkWfQlALYR2aRZ_AIliJ4lc3g'
        self.custom_locust.set_response(
            f"/suite/rest/a/applications/latest/app/design/{object_opaque_id}", 200, read_mock_file("design_landing_page.json"))
        ENV.stats.clear_all()
        sail_form = self.task_set.appian.design.visit_object(object_opaque_id)
        self.assertEqual(type(sail_form), SailUiForm)
        self.assertEqual(0, len(ENV.stats.errors))

    def test_visit_error(self) -> None:
        ENV.stats.clear_all()
        self.custom_locust.set_response(
            "/suite/rest/a/applications/latest/app/design", 400, "")
        with self.assertRaises(Exception) as context:
            sail_form = self.task_set.appian.design.visit()
        # Two errors will be logged, one at the get_page request level, and one at the visit
        self.assertEqual(2, len(ENV.stats.errors))

    def test_create_app_and_record_type(self) -> None:
        if not self.is_integration_mode:
            landing_page = read_mock_file("design_landing_page.json")
            app_landing_page = read_mock_file("design_app_landing_page.json")

            create_object_modal = read_mock_file("design_new_object_modal.json")
            security_page = read_mock_file("design_security_page.json")

            def prepare_create_object() -> None:
                self.custom_locust.enqueue_response(200, create_object_modal)
                self.custom_locust.enqueue_response(200, create_object_modal)
                self.custom_locust.enqueue_response(200, security_page)
            self.custom_locust.enqueue_response(200, landing_page)
            prepare_create_object()
            self.custom_locust.enqueue_response(200, app_landing_page)
            prepare_create_object()
            self.custom_locust.enqueue_response(200, app_landing_page)
            prepare_create_object()
            self.custom_locust.enqueue_response(200, app_landing_page)

        app_form = self.task_set.appian.design.create_application('locust app')
        self.task_set.appian.design.create_record_type(
            app_form, 'my record type')
        self.task_set.appian.design.create_report(app_form, 'my report')


if __name__ == '__main__':
    unittest.main()

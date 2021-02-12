from typing import Any, Dict

from . import logger
from ._interactor import _Interactor
from .helper import find_component_by_attribute_in_dict
from .uiform import SailUiForm

log = logger.getLogger(__name__)


class _TaskOpener:

    def __init__(self, interactor: _Interactor) -> None:
        """Class used to open tasks within sail forms or directly in tempo

        Args:
            session: Locust session/client object
            host (str): Host URL

        """
        self.interactor = interactor

        self._tasks: Dict[str, Any] = dict()

    def accept_a_task(self, payload: str, task_id: str, headers: Dict[str, Any] = {}, task_title: str = "") -> Dict[str, Any]:
        """Accept a task if necessary

        Args:
            payload (str): string to send as part of accepting a task
            task_id (str): task identifier
            headers (Dict[str, Any], optional): Headers to send. Defaults to {}.
            task_title (str, optional): Task title used to describe the interaction. Defaults to "".

        Returns:
            Dict[str, Any]: Response from accepting
        """
        # Appian Tasks require a plain text payload to be informed
        # whether or not the Task has been accepted. Send "assigned" or
        # "accepted" as the payload to manually assign ƒthe tasks state.
        uri = "/suite/rest/a/task/latest/{}/status".format(task_id)
        headers["Accept"] = "application/vnd.appian.tv.ui+json"
        headers["Content-Type"] = "text/plain;charset=UTF-8"

        # The following legacy header allows the server to handle this request.
        # This is only necessary for /suite/rest/a/task/latest/{}/status calls.
        # For reference, see: https://jira.host.net/browse/AN-58600
        headers["X-HTTP-Method-Override"] = "PUT"

        label = f'Tasks.{task_title}.Accept'
        resp = self.interactor.post_page(uri=uri, payload=payload, headers=headers,
                                         label=label)
        return resp.json()

    def visit_by_task_id(self, task_title: str, task_id: str) -> Dict[str, Any]:
        """Visit a task page and get the corresponding json, by its identifier

        Args:
            task_title (str): Label used to identify the task
            task_id (str): Identifier used to access the task

        Returns:
            Dict[str, Any]: [description]
        """
        uri = "/suite/rest/a/task/latest/{}/attributes".format(task_id)
        headers = self.interactor.setup_request_headers(uri)
        label = f'Tasks.{task_title}'
        resp = self.interactor.get_page(uri=uri, label=label, headers=headers).json()

        # If isAutoAcceptable == false, accept the task first then get the form UI
        if not resp["isAutoAcceptable"]:

            # First do a suite/rest/a/task/latest/{}/status call to get the button component
            unaccepted_task_form = self.accept_a_task("assigned", task_id, task_title=task_title, headers=headers)
            accept_button = find_component_by_attribute_in_dict(
                "label",
                "Accept",
                unaccepted_task_form
            )

            # Then post a suite/rest/a/task/latest/{}/form call to trigger a re-evaluation with the task accepted
            uuid = unaccepted_task_form["uuid"]
            context = unaccepted_task_form["context"]
            uri = "/suite/rest/a/task/latest/{}/form".format(task_id)

            label = f'Tasks.{task_title}.Accept'
            accepted_task_form = self.interactor.click_component(
                post_url=uri,
                component=accept_button,
                context=context,
                uuid=uuid,
                label=label
            )
        else:
            # The task does not need to be accepted in this case
            accepted_task_form = self.accept_a_task("accepted", task_id, task_title=task_title, headers=headers)
        return accepted_task_form

    def visit_and_get_form_by_task_id(self, task_title: str, task_id: str) -> SailUiForm:
        """Allows a user to get the SailForm by a task id and title

        Args:
            task_title (str): Title to identify the task
            task_id (str): Id used to navigate to the task

        Returns:
            SailUiForm: Form returned by navigating to the task
        """
        form_uri = "/suite/rest/a/task/latest/{}/status".format(task_id)

        form_json = self.visit_by_task_id(task_title, task_id)
        breadcrumb = f"Tasks.{task_title}"
        return SailUiForm(self.interactor, form_json, form_uri, breadcrumb=breadcrumb)

from ._base import _Base
from ._interactor import _Interactor
from . import logger
from typing import Dict, Any
from .uiform import SailUiForm
from .helper import find_component_by_attribute_in_dict, log_locust_error

log = logger.getLogger(__name__)


class _Tasks(_Base):
    INITIAL_FEED_URI = "/suite/api/feed/tempo?m=menu-tasks&t=t&s=pt&defaultFacets=%255Bstatus-open%255D"

    def __init__(self, interactor: _Interactor) -> None:
        """
        Tasks class wrapping a list of possible activities that can be performed with Appian-Tempo-Tasks

        Warnings: This class is internal and should not be accessed by tests directly. It can be accessed via the "appian" object

        Note: "appian" is created as part of ``AppianTaskSet``'s ``on_start`` function

        Args:
            session: Locust session/client object
            host (str): Host URL

        """
        self.interactor = interactor

        self._tasks: Dict[str, Any] = dict()

    def get_all(self, search_string: str = None) -> Dict[str, Any]:
        """
        Retrieves all the available "tasks" and associated metadata from "Appian-Tempo-Tasks"

        Note: All the retrieved data about tasks is stored in the private variable self._tasks

        Returns (dict): List of tasks and associated metadata

        Examples:

            >>> self.appian.task.get_all()

        """
        next_uri = _Tasks.INITIAL_FEED_URI

        headers = self.interactor.setup_request_headers()
        headers["Accept"] = "application/atom+json; inlineSail=true; recordHeader=true, application/json;"
        self._tasks = dict()

        while next_uri:
            response = self.interactor.get_page(uri=next_uri, headers=headers, label="Tasks").json()
            for current_item in response.get("feed", {}).get("entries", []):
                # Supporting only the SAIL tasks (id starts with "t-" id.)
                if "t-" in current_item.get("id", ""):
                    # assumes only one child is available in general for a task
                    children = current_item.get("content", {}).get("children", [])
                    if len(children) > 0:
                        key = "{}_{}_{}".format(current_item["id"], current_item["title"], children[0])
                        self._tasks[key] = current_item
            feed_data = response.get("feed", {})
            partially_parsed_resp = feed_data.get("links", [])
            if len(partially_parsed_resp) > 0 and partially_parsed_resp[-1].get("rel", []) == "next":
                next_uri_with_hostname = partially_parsed_resp[-1]["href"]
                next_uri = next_uri_with_hostname[len(self.interactor.host):]
            else:
                next_uri = ""
        return self._tasks

    def get_task(self, task_name: str, exact_match: bool = True) -> Dict[str, Any]:
        """
        Get the information about specific task by name.

        Args:
            task_name (str): Name of the task
            exact_match (bool): Should task name match exactly or to be partial match. Default : True

        Returns (dict): Specific task's info

        Raises: In case of task is not found in the system, it throws an "Exception"

        Example:
            If full name of task is known,

            >>> self.appian.task.get("task_name")

            If only partial name is known,

            >>> self.appian.task.get("task_name", exact_match=False)

        """
        _, current_task = super().get(self._tasks, task_name, exact_match)
        if not current_task:
            e = Exception(f'There is no task with name "{task_name}" in the system under test (Exact match = {exact_match})')
            log_locust_error(e, location='_tasks.py/get_task()', raise_error=True)
        return current_task

    def visit(self, task_name: str, exact_match: bool = True) -> Dict[str, Any]:
        """
        This function calls the API for the specific task to get its "form" data

        Args:
            task_name (str): Name of the task to be called.
            exact_match (bool, optional): Should task name match exactly or to be partial match. Default : True

        Returns (dict): Response of task's Get UI call in dictionary

        Examples:

            If full name of task is known,

            >>> self.appian.task.visit("task_name")

            If only partial name is known,

            >>> self.appian.task.visit("task_name", exact_match=False)

        """

        task = self.get_task(task_name, exact_match)

        clean_id = task["id"].replace("t-", "")
        children = task.get("content", {}).get("children", [])
        task_title = children[0]

        # Make the attributes call to determine if task is auto-acceptable
        uri = "/suite/rest/a/task/latest/{}/attributes".format(clean_id)
        headers = self.interactor.setup_request_headers(uri)
        label = f'Tasks.{task_title}'
        resp = self.interactor.get_page(uri=uri, label=label, headers=headers).json()

        # If isAutoAcceptable == false, accept the task first then get the form UI
        if not resp["isAutoAcceptable"]:

            # First do a suite/rest/a/task/latest/{}/status call to get the button component
            unaccepted_task_form = self.accept_a_task("assigned", clean_id, task_title=task_title, headers=headers)
            accept_button = find_component_by_attribute_in_dict(
                "label",
                "Accept",
                unaccepted_task_form
            )

            # Then post a suite/rest/a/task/latest/{}/form call to trigger a re-evaluation with the task accepted
            uuid = unaccepted_task_form["uuid"]
            context = unaccepted_task_form["context"]
            uri = "/suite/rest/a/task/latest/{}/form".format(clean_id)

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
            accepted_task_form = self.accept_a_task("accepted", clean_id, task_title=task_title, headers=headers)
        return accepted_task_form

    def accept_a_task(self, payload: str, clean_id: str, headers: Dict[str, Any] = {}, task_title: str = "") -> Dict[str, Any]:

        # Appian Tasks require a plain text payload to be informed
        # whether or not the Task has been accepted. Send "assigned" or
        # "accepted" as the payload to manually assign ƒthe tasks state.
        uri = "/suite/rest/a/task/latest/{}/status".format(clean_id)
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

    def visit_and_get_form(self, task_name: str, exact_match: bool = True) -> SailUiForm:

        initial_task_resp: dict = self.get_task(task_name, exact_match)
        clean_id = initial_task_resp["id"].replace("t-", "")
        children = initial_task_resp.get("content", {}).get("children", [])
        task_title = children[0]
        form_uri = "/suite/rest/a/task/latest/{}/status".format(clean_id)

        form_json = self.visit(task_name, exact_match)
        breadcrumb = f"Tasks.{task_title}"
        return SailUiForm(self.interactor, form_json, form_uri, breadcrumb=breadcrumb)

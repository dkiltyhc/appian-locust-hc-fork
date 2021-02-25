from typing import Any, Dict

from . import logger
from ._base import _Base
from ._interactor import _Interactor
from ._locust_error_handler import log_locust_error
from ._task_opener import _TaskOpener
from .uiform import SailUiForm

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
        self.task_opener = _TaskOpener(self.interactor)
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
            log_locust_error(e, raise_error=True)
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

        return self.task_opener.visit_by_task_id(task_title, clean_id)

    def visit_and_get_form(self, task_name: str, exact_match: bool = True) -> SailUiForm:
        """
        Gets the SailUiForm given a task name

        Args:
            task_name (str): Name of the task to search for
            exact_match (bool, optional): Whether or not a full match is returned. Defaults to True.

        Returns:
            SailUiForm: SAIL form for the task
        """
        initial_task_resp: dict = self.get_task(task_name, exact_match)
        clean_id = initial_task_resp["id"].replace("t-", "")
        children = initial_task_resp.get("content", {}).get("children", [])
        task_title = children[0]

        form_json = self.task_opener.visit_by_task_id(task_title, clean_id)
        breadcrumb = f"Tasks.{task_title}"
        form_uri = "/suite/rest/a/task/latest/{}/form".format(clean_id)
        return SailUiForm(self.interactor, form_json, form_uri, breadcrumb=breadcrumb)

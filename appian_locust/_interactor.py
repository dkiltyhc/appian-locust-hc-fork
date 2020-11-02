import json
import os
import sys
import urllib.parse
from datetime import datetime
from re import match, search
from typing import Any, Dict, Optional, Set, Tuple

from locust.clients import HttpSession, ResponseContextManager
from requests import Response

from ._save_request_builder import save_builder
from .helper import (find_component_by_attribute_in_dict, list_filter,
                     log_locust_error, test_response_for_error, get_username)
from . import logger
from .exceptions import BadCredentialsException, MissingCsrfTokenException

log = logger.getLogger(__name__)

# TODO: Consider breaking this class up into smaller pieces


RECORD_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "recorded_files")


class _Interactor:
    def __init__(self, session: HttpSession, host: str) -> None:
        """
        Class that represents interactions with the UI and Appian system
        If you want to record all requests made, you can set the record_mode attribute
        on the client, see the mock_client.py in the tests directory as an example

        >>> setattr(self.client, 'record_mode', True)

        Args:
            session: Locust session/client object
            host (str): Host URL inherited from subclass to conform with Mypy standards
        """
        self.client = session
        self.host = host
        self.record_mode = True if hasattr(self.client, "record_mode") else False
        self.datatype_cache = DataTypeCache()
        self.user_agent = ""
        # Set to default as desktop request.
        self.set_user_agent_to_desktop()

    # GENERIC UTILITY METHODS
    def set_user_agent_to_desktop(self) -> None:
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36"

    def set_user_agent_to_mobile(self) -> None:
        self.user_agent = "AppianAndroid/20.2 (Google AOSP on IA Emulator, 9; Build 0-SNAPSHOT; AppianPhone)"

    def setup_request_headers(self, uri: str = None) -> dict:
        """
        Generates standard headers for session

        Args:
            uri (str): URI to be assigned as the Referer

        Returns (dict): headers

        Examples:

            >>> self.setup_request_headers()
        """

        uri = uri if uri is not None else self.host
        headers = {
            "Accept": "application/atom+json,application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en_US",
            "Connection": "keep-alive",
            "User-Agent": self.user_agent,
            "Referer": uri + "/suite/tempo/",
            "X-Appian-Cached-Datatypes": self.datatype_cache.get(),
            "Cookie": "JSESSIONID={}; __appianCsrfToken={}; __appianMultipartCsrfToken={}".format(
                self.client.cookies.get("JSESSIONID", ""),
                self.client.cookies.get("__appianCsrfToken", ""),
                self.client.cookies.get("__appianMultipartCsrfToken", ""),
            ),
            "DNT": "1",
            "X-APPIAN-CSRF-TOKEN": self.client.cookies.get("__appianCsrfToken", ""),
            "X-APPIAN-MP-CSRF-TOKEN": self.client.cookies.get("__appianMultipartCsrfToken", ""),
            "X-Appian-Ui-State": "stateful",
            "X-Appian-Features": self.client.feature_flag,
            "X-Appian-Features-Extended": self.client.feature_flag_extended,
            "x-libraries-suppress-www-authenticate": "true",
            # this should probably go...
            "X-Atom-Content-Type": "application/html"
        }
        return headers

    def setup_sail_headers(self) -> dict:
        headers = self.setup_request_headers()
        headers.update({'Content-Type': 'application/vnd.appian.tv+json',
                        'Accept': 'application/vnd.appian.tv.ui+json'})
        return headers

    # Headers needed for Record View request, which returns a feed object
    def setup_feed_headers(self) -> dict:
        headers = self.setup_request_headers()
        headers["Accept"] = "application/atom+json; inlineSail=true; recordHeader=true"
        headers["Accept"] = headers["Accept"] + ", application/json; inlineSail=true; recordHeader=true"
        return headers

    def replace_base_path_if_appropriate(self, uri: str) -> str:
        if hasattr(self.client, "base_path_override") and self.client.base_path_override and \
                self.client.base_path_override != '/suite':
            return uri.replace('/suite', self.client.base_path_override, 1)
        return uri

    def post_page(self, uri: str, payload: Any = {}, headers: Dict[str, Any] = None, label: str = None, files: dict = None, check_login: bool = True) -> Response:
        """
        Given a uri, executes POST request and returns response

        Args:
            uri: API URI to be called
            payload: Body of the API request. Can be either JSON or text input to allow for different payload types.
            headers: header for the REST API Call
            label: the label to be displayed by locust

        Returns: Json response of post operation

        """

        if headers is None:
            headers = self.setup_sail_headers()

        uri = self.replace_base_path_if_appropriate(uri)
        username = get_username(self.auth)
        if files:  # When a file is specified, don't send any data in the 'data' field
            post_payload = None
        elif isinstance(payload, dict):
            post_payload = json.dumps(payload).encode()
        elif isinstance(payload, str):
            post_payload = payload.encode()
        else:
            log_locust_error(
                Exception("Cannot POST a payload that is not of type dict or string"),
                location="_interactor.py/post_page")
            sys.exit(1)
        with self.client.post(uri, data=post_payload, headers=headers, name=label, files=files, catch_response=True) as resp:  # type: ResponseContextManager
            try:
                test_response_for_error(resp, uri, raise_error=check_login, username=username)
            except Exception as e:
                raise e
            else:
                if check_login:
                    resp.raise_for_status()
            if self.record_mode:
                self.write_response_to_lib_folder(label, resp)
            return resp

    def login(self, auth: list = None) -> Tuple[HttpSession, Response]:
        if auth is not None:
            self.auth = auth
        """
        Login to Appian Tempo using given auth

        Args:
            auth: list containing 2 elements. username and password

        Returns: Locust client and response
        """

        uri = self.host + "/suite/"

        # load initial page to get tokens/cookies
        token_uri = uri + '?signin=native'
        resp = self.get_page(token_uri, label="Login.LoadUi", check_login=False)
        payload = {
            "un": self.auth[0],
            "pw": self.auth[1],
            "_spring_security_remember_me": "on",
            "X-APPIAN-CSRF-TOKEN": resp.cookies["__appianCsrfToken"],
        }

        # override headers for login use case
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Upgrade-Insecure-Requests": "1",
            "Referer": self.host,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36",
        }

        # Post Auth
        resp = self.post_page(
            uri + "auth?appian_environment=tempo",
            payload=urllib.parse.urlencode(payload),
            headers=headers,
            label="Login.SubmitAuth",
            check_login=False)
        if not resp or not resp.ok:
            raise BadCredentialsException()
        elif "__appianMultipartCsrfToken" not in self.client.cookies:
            raise MissingCsrfTokenException(self.client.cookies)
        return self.client, resp

    def check_login(self, resp: ResponseContextManager) -> None:
        """
        Given a response, checks to see if it's possible that we are not logged in and then performs a login if we are not

        Args:
            resp: Response to check

        Returns: None
        """
        is_login_page = '__appianCsrfToken' in resp.cookies
        if resp.ok and is_login_page:
            self.login()
        elif not resp.ok:
            # Check login page actually returns a csrf token
            login_page_resp = self.get_page('/suite/', label="Login.LoadUi", check_login=False)
            if login_page_resp.ok and '__appianCsrfToken' in login_page_resp.cookies:
                self.login()

    def get_page(self, uri: str, headers: Optional[Dict[str, Any]] = None, label: str = None, check_login: bool = True) -> Response:
        """
        Given a uri, executes GET request and returns response

        Args:
            uri: API URI to be called
            headers: header for the REST API Call
            label: the label to be displayed by locust
            check_login: optional boolean to bypass checking if we are logged in

        Returns: Json response of GET operation
        """
        if headers is None:
            headers = self.setup_request_headers(uri)

        kwargs: Dict[str, Any] = {'name': label, 'catch_response': True}

        username = get_username(self.auth)
        uri = self.replace_base_path_if_appropriate(uri)
        if headers is not None:
            kwargs['headers'] = headers
        with self.client.get(uri, **kwargs) as resp:  # type: ResponseContextManager
            if check_login:
                self.check_login(resp)
            test_response_for_error(resp, uri, raise_error=check_login, username=username)
            if self.record_mode:
                self.write_response_to_lib_folder(label, resp)
            return resp

    def get_webapi(self, uri: str, headers: Dict[str, Any] = None, label: str = None, queryparameters: Dict[str, Any] = {}) -> Response:
        """
        Same as ``get_page``. Additionally it accepts the query parameter to add query parameter while running "GET" operation
        Args:
            uri: API URI to be called
            headers: header for the REST API Call
            label: the label to be displayed by locust
            queryparameters: Queries/Filters

        Returns: Json response of GET operation

        """
        querystring = []
        for k, v in queryparameters.items():
            querystring.append("{}={}".format(k, v))

        uri += "?" + "&".join(querystring)
        resp = self.get_page(uri, headers=headers, label=label)
        if self.record_mode:
            self.write_response_to_lib_folder(label, resp)
        return resp

    def upload_document_to_server(self, file_path: str, is_encrypted: bool = False) -> int:
        '''
        Uploads a document to the server, so that it can be used in upload fields
        Args:
            uri: API URI to be called
            file_path: Path to the file to be uploaded

        Returns: Document Id that can be used for upload fields
        ''',

        # Override default headers to avoid sending SAIL headers here
        headers = self.setup_request_headers()
        if is_encrypted:
            headers['encrypted'] = 'true'
        with open(file_path, 'rb') as f:
            resp_label = "Document.Upload." + os.path.basename(file_path).strip(" .")
            files = {"file": f}
            response = self.post_page(
                "/suite/api/tempo/file?validateExtension=false",
                headers=headers,
                label=resp_label,
                files=files)
            if self.record_mode:
                self.write_response_to_lib_folder(resp_label, response)
            else:
                response.raise_for_status()
            doc_id = response.json()[0]["id"]
            return doc_id

    def write_response_to_lib_folder(self, label: Optional[str], response: Response) -> None:
        """
        Used for internal testing, to grab the response and put it in a file of type JSON

        Args:
            label(Optional[str]): Optional label, used to name the file
            response(Response): Response object to write to a file

        Writes to the current folder that _interactor is in, meaning you may have to search in
        your virtualenv if not running appian_locust in its own repository
        """
        cleaned_label = label.replace("/", "|") if label else "response"
        file_name = cleaned_label + " " + str(datetime.now())
        file_ending = ".json"
        if not os.path.exists(RECORD_PATH):
            os.mkdir(RECORD_PATH)
        proposed_file_name = os.path.join(RECORD_PATH, file_name + file_ending)
        # Cover files with the same name case
        while os.path.exists(proposed_file_name):
            length_of_file_type = len(file_ending)
            proposed_file_name = proposed_file_name[:-length_of_file_type] + " (1)" + file_ending
        with open(proposed_file_name, 'w') as f:
            f.write(response.text)

    def click_record_link(self, get_url: str, component: Dict[str, Any], context: Dict[str, Any],
                          label: str = None, headers: Dict[str, Any] = None, locust_label: str = "") -> Dict[str, Any]:
        '''
        Use this function to interact specifically with record links, which represent links to new sail forms.
        Args:
            get_url: the url (not including the host and domain) to navigate to
            component: the JSON code for the RecordLink
            context: the Sail context parsed from the json response
            label: the label to be displayed by locust for this action
            headers: header for the REST API call

        Returns: the response of get RecordLink operation as json
        '''

        # The record links in record instance view tabs are 1 level further down
        if '_recordRef' not in component:
            # This is probably a record view link with the link information 1 level further down
            component = component.get('link', "")
        record_ref = component.get('_recordRef', "")

        # Support record views other than /summary by checking the dashboard attribute
        dashboard = component.get('dashboard', "")
        if not dashboard:
            dashboard = "summary"
        record_view_url_stub = f"/view/{dashboard}"
        if not record_ref:
            e = Exception("Cannot find _recordRef attribute in RecordLink component.")
            log_locust_error(
                e,
                location="_interactor.py/click_record_link()",
                raise_error=True
            )
        record_link_url_suffix = record_ref + record_view_url_stub

        # Logic to construct record link URL in tempo and sites
        if "tempo" in get_url:
            record_link_url = "/suite/tempo/records/item/" + record_link_url_suffix
        elif "sites" in get_url and "/record/" in get_url:
            parse_pattern = "/record/"
            record_link_url = get_url[:get_url.index(parse_pattern)+len(parse_pattern)] + record_link_url_suffix
        elif match(r'.*\/page\/\w+$', get_url):
            record_link_url = get_url + "/record/" + record_link_url_suffix
        # Support record links on site pages
        elif "sites" in get_url and "/report" in get_url and "/pages/" in get_url:
            page_search = search(r'(?<=\/pages\/)\w+', get_url)
            if page_search:
                page_name = page_search.group()
            else:
                e = Exception("Unexpected record link URL - couldn't find page name after /pages/")
                log_locust_error(
                    e,
                    location="_interactor.py/click_record_link()",
                    raise_error=True
                )
            parse_pattern = page_name + "/report"
            url_prefix_index = get_url.index(parse_pattern) + len(page_name)
            # record_link_url = get_url[:get_url.index(parse_pattern) + len(page_name)].replace("/pages/",
            record_link_url = get_url[:url_prefix_index].replace("/pages/", "/page/") + "/record/" + record_link_url_suffix
        # Support record view links from a record within a site
        elif "record" in get_url:
            site_name = component.get('siteUrlStub', "")
            page_name = component.get('pageUrlStub', "")
            record_link_url = f"/suite/rest/a/sites/latest/{site_name}/page/{page_name}/record/{record_link_url_suffix}"
        else:
            e = Exception("Unexpected record link URL")
            log_locust_error(
                e,
                location="_interactor.py/click_record_link()",
                raise_error=True
            )

        if not get_url or not record_link_url:
            e = Exception("Cannot make Record Link request.")
            log_locust_error(
                e,
                location="_interactor.py/click_record_link()",
                raise_error=True
            )

        # Clicking a record link returns a record instance feed - use setup_feed_headers to get the correct headers
        headers = self.setup_feed_headers()

        locust_label = locust_label or "Clicking RecordLink: " + component["label"]

        resp = self.get_page(
            self.host + record_link_url, headers=headers, label=locust_label
        )
        return resp.json()

    def click_start_process_link(self, label: str, component: Dict[str, Any], process_model_opaque_id: str,
                                 cache_key: str, site_name: str, page_name: str, is_mobile: bool = False,
                                 locust_request_label: str = None) -> Dict[str, Any]:
        '''
        Use this function to interact with start process links, which start a process and return the
        start form.
        Args:
            component: the JSON representing the Start Process Link
            process_model_opaque_id: opaque id for the process model of the Start Process Link
            cache_key: cachekey for the start process link
            site_name: name of site for link in starting process model.
            page_name: name of page for link in starting process model.
            is_mobile: indicates if it should hit the mobile endpoint.
            locust_request_label: label to be used within locust

        Returns: the response of get Start Process Link operation as json
        '''
        if is_mobile:
            spl_link_url = f"/suite/rest/a/model/latest/startProcess/{process_model_opaque_id}?cacheKey={cache_key}"
        else:
            spl_link_url = f"/suite/rest/a/sites/latest/{site_name}/page/{page_name}/startProcess/{process_model_opaque_id}?cacheKey={cache_key}"

        headers = self.setup_request_headers()
        headers["Accept"] = "application/vnd.appian.tv.ui+json"
        headers["Content-Type"] = "application/vnd.appian.tv+json"

        locust_label = locust_request_label or "Clicking StartProcessLink: " + component["label"]
        resp = self.post_page(
            self.host + spl_link_url, payload={}, headers=headers, label=locust_label
        )
        return resp.json()

    def click_related_action(self, component: Dict[str, Any], record_type_stub: str, opaque_record_id: str,
                             opaque_related_action_id: str, locust_request_label: str = "") -> Dict[str, Any]:
        '''
        Use this function to interact with related action links, which start a process and return the
        start form.
        Args:
            component: the JSON representing the Related Action Link
            record_type_stub: record type stub for the record
            opaque_record_id: opaque id for the record
            opaque_related_action_id: opaque id for the related action
            locust_request_label: label to be used within locust

        Returns: the start form for the related action
        '''
        # Mobile url not implemented
        # Web url:
        related_action_link_url = f"/suite/rest/a/record/latest/{record_type_stub}/{opaque_record_id}/actions/{opaque_related_action_id}"

        headers = self.setup_request_headers()
        headers["Accept"] = "application/vnd.appian.tv.ui+json"
        headers["Content-Type"] = "application/vnd.appian.tv+json"

        locust_label = locust_request_label or "Clicking RelatedActionLink: " + component["label"]
        resp = self.post_page(
            self.host + related_action_link_url, payload={}, headers=headers, label=locust_label
        )
        return resp.json()

    # COMPONENT RELATED METHODS

    def click_component(self, post_url: str, component: Dict[str, Any], context: Dict[str, Any],
                        uuid: str, label: str = None, headers: Dict[str, Any] = None, client_mode: str = None) -> Dict[str, Any]:
        '''
            Calls the post operation to click certain SAIL components such as Buttons and Dynamic Links

            Args:
                post_url: the url (not including the host and domain) to post to
                component: the JSON code for the desired component
                context: the Sail context parsed from the json response
                uuid: the uuid parsed from the json response
                label: the label to be displayed by locust for this action
                headers: header for the REST API call

            Returns: the response of post operation as json
        '''
        if "link" in component:
            wrapper_label = component["label"]
            component = component["link"]
            component["label"] = wrapper_label

        payload = save_builder()\
            .component(component)\
            .context(context)\
            .uuid(uuid)\
            .build()

        locust_label = label or f'Click \'{component["label"]}\' Component'

        resp = self.post_page(
            self.host + post_url, payload=payload, label=locust_label
        )
        return resp.json()

    # Aliases for click_component to preserve backwards compatibiltiy and increase readability
    click_button = click_component
    click_link = click_component

    def send_dropdown_update(self, post_url: str, dropdown: Dict[str, Any],
                             context: Dict[str, Any], uuid: str, index: int, label: str = None) -> Dict[str, Any]:
        '''
            Calls the post operation to send an update to a dropdown

            Args:
                post_url: the url (not including the host and domain) to post to
                dropdown: the JSON code for the desired dropdown
                context: the Sail context parsed from the json response
                uuid: the uuid parsed from the json response
                index: location of the dropdown value
                label: the label to be displayed by locust for this action
                headers: header for the REST API call

            Returns: the response of post operation as json
        '''
        new_value = {
            "#t": "Integer",
            "#v": index
        }
        payload = save_builder()\
            .component(dropdown)\
            .context(context)\
            .uuid(uuid)\
            .value(new_value)\
            .build()

        locust_label = label or f'Select \'{dropdown["label"]}\' Dropdown'

        resp = self.post_page(
            self.host + post_url, payload=payload, label=locust_label
        )
        return resp.json()

    def get_primary_button_payload(self, page_content_in_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Finds the primary button from the page content response and creates the payload which can be used to simulate a click

        Args:
            page_content_in_json: full page content that has a primary button

        Returns: payload of the primary button

        """
        primary_button = page_content_in_json["ui"]["contents"][0]["buttons"]["primaryButtons"][0]
        primary_button["#t"] = "ButtonWidget"
        context = page_content_in_json["context"]
        uuid = page_content_in_json["uuid"]
        payload = save_builder()\
            .component(primary_button)\
            .context(context)\
            .uuid(uuid)\
            .build()

        return payload

    def fill_textfield(self, post_url: str, text_field: Dict[str, Any], text: str,
                       context: Dict[str, Any], uuid: str, label: str = None) -> Dict[str, Any]:
        """
        Fill a TextField with the given text
        Args:
            post_url: the url (not including the host and domain) to post to
            text_field: the text field component returned from find_component_by_attribute_in_dict
            text: the text to fill into the text field
            context: the Sail context parsed from the json response
            uuid: the uuid parsed from the json response
            label: the label to be displayed by locust for this action

        Returns: the response of post operation as json

        """
        new_value = {"#t": "Text", "#v": text}
        payload = save_builder()\
            .component(text_field)\
            .context(context)\
            .uuid(uuid)\
            .value(new_value)\
            .build()

        locust_label = label or f'Fill \'{text_field["label"]}\' TextField'

        resp = self.post_page(
            self.host + post_url, payload=payload, label=locust_label
        )
        return resp.json()

    def fill_pickerfield_text(self, post_url: str, picker_field: Dict[str, Any], text: str,
                              context: Dict[str, Any], uuid: str, label: str = None) -> Dict[str, Any]:
        """
        Fill a Picker field with the given text and randomly select one of the suggested item
        Args:
            post_url: the url (not including the host and domain) to post to
            picker_field: the picker field component returned from find_component_by_attribute_in_dict
            text: the text to fill into the picker field
            context: the SAIL context parsed from the json response
            uuid: the uuid parsed from the json response
            label: the label to be displayed by locust for this action

        Returns: the response of post operation as json

        """
        new_value = {
            "#t": "PickerData",
            "typedText": text
        }

        payload = save_builder()\
            .component(picker_field)\
            .context(context)\
            .uuid(uuid)\
            .value(new_value)\
            .build()

        locust_label = label or f'Fill \'{picker_field["label"]}\' PickerField'

        resp = self.post_page(
            self.host + post_url, payload=payload, label=locust_label
        )
        return resp.json()

    def select_pickerfield_suggestion(self, post_url: str, picker_field: Dict[str, Any], selection: Dict[str, Any],
                                      context: Dict[str, Any], uuid: str, label: str = None) -> Dict[str, Any]:
        """
        Select a Picker field from available selections
        Args:
            post_url: the url (not including the host and domain) to post to
            picker_field: the text field component returned from find_component_by_attribute_in_dict
            selection: the suggested item to select for the picker field
            context: the SAIL context parsed from the json response
            uuid: the uuid parsed from the json response
            label: the label to be displayed by locust for this action

        Returns: the response of post operation as json

        """
        identifiers_list = []
        identifiers_list.append(selection)

        new_value = {
            "#t": "PickerData",
            "identifiers": identifiers_list
        }

        payload = save_builder()\
            .component(picker_field)\
            .context(context)\
            .uuid(uuid)\
            .value(new_value)\
            .build()

        locust_label = label or f'Fill \'{picker_field["label"]}\' PickerField'

        resp = self.post_page(
            self.host + post_url, payload=payload, label=locust_label
        )
        return resp.json()

    def select_checkbox_item(self, post_url: str, checkbox: Dict[str, Any],
                             context: Dict[str, Any], uuid: str, indices: list, context_label: str = None) -> Dict[str, Any]:
        '''
            Calls the post operation to send an update to a checkbox to check all appropriate boxes

            Args:
                post_url: the url (not including the host and domain) to post to
                checkbox: the JSON representing the desired checkbox
                context: the Sail context parsed from the json response
                uuid: the uuid parsed from the json response
                indices: indices of the checkbox
                label: the label to be displayed by locust for this action
                headers: header for the REST API call

            Returns: the response of post operation as json
        '''
        new_value = {
            "#t": "Integer?list",
            "#v": indices if indices else None
        }
        payload = save_builder()\
            .component(checkbox)\
            .context(context)\
            .uuid(uuid)\
            .value(new_value)\
            .build()

        locust_label = context_label or "Checking boxes for " + checkbox.get("testLabel", checkbox.get("label", "label-not-found"))

        resp = self.post_page(
            self.host + post_url, payload=payload, label=locust_label
        )
        return resp.json()

    def click_selected_tab(self, post_url: str, tab_group_component: Dict[str, Any], tab_label: str,
                           context: Dict[str, Any], uuid: str) -> Dict[str, Any]:
        '''
            Calls the post operation to send an update to a tabgroup to select a tab

            Args:
                post_url: the url (not including the host and domain) to post to
                tab_group_component: the JSON representing the desired TabButtonGroup SAIL component
                tab_label: Label of the tab to select
                context: the Sail context parsed from the json response
                uuid: the uuid parsed from the json response
                label: the label of the tab to select. It is one of the tabs inside TabButtonGroup

            Returns: the response of post operation as json
        '''
        tabs_list = tab_group_component["tabs"]
        tab_index = 0
        for index, tab in enumerate(tabs_list):
            if isinstance(tab, dict) and find_component_by_attribute_in_dict("label", tab_label, tab) is not None:
                tab_index = index + 1
                break

        if tab_index:
            new_value = {
                "#t": "Integer",
                "#v": tab_index
            }
        else:
            raise Exception(f"Cannot click a tab with label: '{tab_label}' inside the TabButtonGroup component")

        payload = save_builder()\
            .component(tab_group_component)\
            .context(context)\
            .uuid(uuid)\
            .value(new_value)\
            .build()

        locust_label = f"Selecting tab with label: '{tab_label}' inside TabButtonGroup component"

        resp = self.post_page(
            self.host + post_url, payload=payload, label=locust_label
        )
        return resp.json()

    def select_radio_button(self, post_url: str, buttons: Dict[str, Any], context: Dict[str, Any],
                            uuid: str, index: int, context_label: str = None) -> Dict[str, Any]:
        '''
            Calls the post operation to send an update to a radio button to select the appropriate button

            Args:
                post_url: the url (not including the host and domain) to post to
                buttons: the JSON representing the desired radio button field
                context: the Sail context parsed from the json response
                uuid: the uuid parsed from the json response
                index: index of the button to be selected
                label: the label to be displayed by locust for this action
                headers: header for the REST API call

            Returns: the response of post operation as json
        '''
        new_value = {
            "#t": "Integer",
            "#v": index
        }
        payload = save_builder()\
            .component(buttons)\
            .context(context)\
            .uuid(uuid)\
            .value(new_value)\
            .build()

        resp = self.post_page(
            self.host + post_url, payload=payload, label=context_label
        )
        return resp.json()

    def upload_document_to_field(self, post_url: str, upload_field: Dict[str, Any],
                                 context: Dict[str, Any], uuid: str, doc_id: int,
                                 locust_label: str = None, client_mode: str = 'DESIGN') -> Dict[str, Any]:
        '''
            Calls the post operation to send an update to a upload_field to upload a document.
            Requires a previously uploaded document id

            Args:
                post_url: the url (not including the host and domain) to post to
                checkbox: the JSON representing the desired checkbox
                context: the Sail context parsed from the json response
                uuid: the uuid parsed from the json response
                indices: indices of the checkbox
                context_label: the label to be displayed by locust for this action
                client_mode: where this is being uploaded to, defaults to DESIGN

            Returns: the response of post operation as json
        '''
        new_value = {
            "#t": "CollaborationDocument",
            "id": doc_id
        }
        payload = save_builder()\
            .component(upload_field)\
            .context(context)\
            .uuid(uuid)\
            .value(new_value)\
            .build()

        locust_label = locust_label or "Uploading Document to " + \
            upload_field.get("label", upload_field.get("testLabel", "Generic FileUpload"))
        # Override the default headers here
        headers = self.setup_sail_headers()
        headers['X-Client-Mode'] = client_mode
        resp = self.post_page(
            self.host + post_url, payload=payload, headers=headers, label=locust_label
        )
        return resp.json()

    def update_grid_from_sail_form(self, post_url: str,
                                   grid_component: Dict[str, Any], new_grid_save_value: Dict[str, Any],
                                   context: Dict[str, Any], uuid: str,
                                   context_label: str = None) -> Dict[str, Any]:
        """
            Calls the post operation to send a grid update

            Args:
                post_url: the url (not including the host and domain) to post to
                grid_component: the JSON dict representing the grid to update
                context: the Sail context parsed from the json response
                uuid: the uuid parsed from the json response
                uuid: indices of the checkbox
                context_label: the label to be displayed by locust for this action

            Returns: the response of post operation as jso
        """
        payload = save_builder()\
            .component(grid_component)\
            .context(context)\
            .uuid(uuid)\
            .value(new_grid_save_value)\
            .build()

        locust_label = context_label or "Updating Grid " + grid_component.get("label", "")
        resp = self.post_page(
            self.host + post_url, payload=payload, label=locust_label
        )
        return resp.json()

    def interact_with_record_grid(self, post_url: str,
                                  grid_component: Dict[str, Any],
                                  context: Dict[str, Any], uuid: str,
                                  context_label: str = None) -> Dict[str, Any]:
        """
            Calls the post operation to send a record grid update

            Args:
                post_url: the url (not including the host and domain) to post to
                grid_component: the JSON dict representing the grid to update
                context: the Sail context parsed from the json response
                uuid: the uuid parsed from the json response
                context_label: the label to be displayed by locust for this action

            Returns: the response of post operation as jso
        """
        url_stub = post_url.split('/')[-1]
        payload = save_builder()\
            .component(grid_component)\
            .context(context)\
            .uuid(uuid)\
            .record_url_stub(url_stub)\
            .build()

        locust_label = context_label or "Updating Record Grid " + grid_component.get("label", "")
        resp = self.post_page(
            self.host + post_url, payload=payload, label=locust_label
        )
        resp.raise_for_status()
        return resp.json()


class DataTypeCache(object):
    def __init__(self) -> None:
        """
        This class provides a structure to handle data type cache
        """
        self._cached_datatype: Set[str] = set()

    def clear(self) -> None:
        """
        Clears the data type cache
        """
        self._cached_datatype.clear()

    def cache(self, response_in_json: Dict[str, Any]) -> None:
        """
        From the given json response, finds and caches the data type
        Args:
            response_in_json: response of the API request

        """
        if response_in_json is not None and "#s" in response_in_json \
                and response_in_json.get("#s", {}).get("#t", "").endswith("DataType?list"):
            for dt in response_in_json["#s"]["#v"]:
                self._cached_datatype.add(str(dt["id"]))

    def get(self) -> str:
        """
        Concatenates all cached data types and returns a string

        Returns: concatenated cached data type string
        """
        return ",".join(self._cached_datatype)
import enum
import errno
import json
import os
import random
import warnings
from functools import wraps
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote, urlparse

from appian_locust.records_helper import _is_grid

from . import logger
from ._grid_interactor import GridInteractor
from ._interactor import _Interactor
from ._ui_reconciler import UiReconciler
from .helper import (extract_all_by_label,
                     find_component_by_attribute_in_dict,
                     find_component_by_index_in_dict,
                     find_component_by_label_and_type_dict, log_locust_error)
from .records_helper import (get_record_header_response,
                             get_record_summary_view_response)

KEY_UUID = "uuid"
KEY_CONTEXT = "context"
COMPONENTS_THAT_CAN_BE_FILLED = ["ParagraphField", "TextField"]

log = logger.getLogger(__name__)


class ClientMode(enum.Enum):
    TEMPO = 'TEMPO'
    DESIGN = 'DESIGN'


def raises_locust_error(location: str) -> Callable:
    def should_log_loc_error(func: Callable) -> Callable:
        @wraps(func)
        def func_wrapper(*args: Any, **kwargs: Any) -> Optional[Callable]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_locust_error(e, location=location, raise_error=True)
                return None
        return func_wrapper
    return should_log_loc_error


class SailUiForm:
    def __init__(self, interactor: _Interactor, state: Dict[str, Any], url: str, breadcrumb: str = "SailUi"):
        """
        UIForm Class used to interact with a SAIL form used in an action, record, etc..

        Args:
            base: Action, Record, etc.. interactor object
            state: JSON representation of the initial form
            latest_state: JSON representation of the last to the the form
            url: Url to make updates to the form
            breadcrumbs: Path used to create locust labels

        """
        self.interactor: _Interactor = interactor
        self.state: Dict[str, Any] = state
        self.form_url = url
        if any(key not in self.state for key in (KEY_CONTEXT, KEY_UUID)):
            return None
        self.context: dict = self.state[KEY_CONTEXT]
        self.uuid: str = self.state[KEY_UUID]
        self.grid_interactor: GridInteractor = GridInteractor()
        self.reconciler: UiReconciler = UiReconciler()
        self.breadcrumb = breadcrumb

        # Cache data types on opening new form
        self.interactor.datatype_cache.cache(self.state)

    def get_response(self) -> Optional[Dict[str, Any]]:
        """
        Latest state response

        Returns (dict): The last recorded response

        """
        warnings.warn("The method 'get_response' is deprecated, just do 'self.state' to get the latest returned value")
        return self.state

    @property
    def latest_state(self) -> Optional[Dict[str, Any]]:
        """
        Latest state response

        Returns (dict): The last recorded response

        """
        warnings.warn("The method 'latest_state' is deprecated, just do 'self.state' on the last returned value")
        return self.state

    def get_latest_form(self) -> 'SailUiForm':
        """
        Latest ui form

        Returns (dict): The ui form with its current ui

        """
        warnings.warn("The method 'get_latest_form' is deprecated, "
                      "ui is now updated on each call, you can just chain methods without calling `get_latest_form`")
        return self

    def __str__(self) -> str:
        return f"self_state={json.dumps(self.state,indent=4)}"

    # TODO: Handle components on a page with the same label

    @raises_locust_error("uiform.py/fill_text_field()")
    def fill_text_field(self, label: str, value: str, locust_request_label: str = "") -> 'SailUiForm':
        """
        Fills a field on the form, if there is one present with the following label (case sensitive)
        Otherwise throws a NotFoundException

        Args:
            label(str): Label of the field to fill out
            value(str): Value to update the label to

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.fill_text_field('Title','My New Novel')

        """
        component = find_component_by_attribute_in_dict(
            'label', label, self.state)
        self._validate_component_found(component, label)

        reeval_url = self._get_update_url_for_reeval(self.state)
        locust_label = locust_request_label or f"{self.breadcrumb}.FillTextField.{label}"
        new_state = self.interactor.fill_textfield(
            reeval_url, component, value, self.context, self.uuid, label=locust_label)
        if not new_state:
            raise Exception(f"No response returned when trying to update field with label '{label}'")

        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/fill_field_by_index()")
    def fill_field_by_index(self, type_of_component: str, index: int, text_to_fill: str, locust_request_label: str = "") -> 'SailUiForm':
        """
        Selects a Field by its index and fills it with a text value

        Args:
            type_of_component(str): Name of the componen to fill
            index(int): Index of the field on the page (is it the first one found, or second etc.)
            value(int): Value to fill in the field of type 'type_of_component'

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.fill_field_by_index("ParagraphField", 1, "Hello, Testing")
            # selects the first ParagraphField with the value "Hello, Testing"

        """
        component = find_component_by_index_in_dict(type_of_component, index, self.state)
        reeval_url = self._get_update_url_for_reeval(self.state)
        locust_label = locust_request_label or f"{self.breadcrumb}.FillTextFieldByIndex.{index}"
        new_state = self.interactor.fill_textfield(
            reeval_url, component, text_to_fill, self.context, self.uuid, label=locust_label)
        if not new_state:
            raise Exception(
                f'''
                    No response returned when trying to fill: '{text_to_fill}' in the component: '{type_of_component}'
                    with index: '{index}' on the current page")
                ''')

        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/fill_field_by_any_attribute()")
    def fill_field_by_any_attribute(self, attribute: str, value_for_attribute: str, text_to_fill: str, locust_request_label: str = "") -> 'SailUiForm':
        """
        Selects a Field by "attribute" and its value provided "value_for_attribute"
        and fills it with text "text_to_fill"

        Args:
            attribute(str): Name of the componen to fill
            value_for_attribute(int): Value for the attribute passed in to this function
            text_to_fill(int): Value to fill in the field of type 'type_of_component'

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.fill_field_by_any_attribute("placeholder", "Write a comment", "Hello, Testing")
            # selects the Component with the "placeholder" attribute having "Write a comment" value
            # and fills it with "Hello, Testing"

        """
        component = find_component_by_attribute_in_dict(attribute, value_for_attribute, self.state)
        if component is None:
            raise Exception(f"No such component found with attribute: '{attribute}' and its value: '{value_for_attribute}''")

        if component.get("#t", "") not in COMPONENTS_THAT_CAN_BE_FILLED:
            raise Exception(
                f'''
                    The Component found with attribute: '{attribute}' and its value: '{value_for_attribute}'
                    is not a component that can be filled")
                ''')

        reeval_url = self._get_update_url_for_reeval(self.state)
        locust_label = locust_request_label or f"{self.breadcrumb}.FillTextFieldByAttribute.{attribute}"
        new_state = self.interactor.fill_textfield(
            reeval_url, component, text_to_fill, self.context, self.uuid, label=locust_label)
        if not new_state:
            raise Exception(
                f'''
                    No response returned when trying to fill: '{text_to_fill}' in the component found with attribute: '{attribute}'
                    and its value: '{value_for_attribute}' on the current page")
                ''')

        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    # Aliases for fill_text_field() function
    fill_paragraph_field = fill_text_field

    @raises_locust_error("uiform.py/fill_picker_field()")
    def fill_picker_field(self, label: str, value: str, fill_request_label: str = "", pick_request_label: str = "") -> 'SailUiForm':
        """
        Enters the value in the picker widget and selects one of the suggested items
        if the widget is present with the following label (case sensitive)

        If there is more than one suggestion, this method will select a random one out of the list

        Otherwise this throws a NotFoundException

        The mechanism it uses to find a pickerWidget is prefixing the picker field label with test- and looking for a testLabel

        Args:
            label(str): Label of the field to fill out
            value(str): Value to update the label to

        Keyword Args:
            fill_request_label(str): Label to associate in locust statistics with filling the picker field
            pick_request_label(str): Label to associate in locust statistics with selecting the picker suggestion

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.fill_picker_field('Title','My New Novel')
            >>> form.fill_picker_field('People','Jeff George')

        """
        # pickerFieldCustom will add a test-Label at the level where the suggestions/saveInto exist
        test_label = f'test-{label}'
        component = find_component_by_label_and_type_dict('testLabel', test_label, 'PickerWidget', self.state)

        locust_label = fill_request_label or f"{self.breadcrumb}.FillPickerField.{label}"
        new_state = self.interactor.fill_pickerfield_text(
            self.form_url, component, value, self.context, self.uuid, label=locust_label)

        if not new_state:
            raise Exception(f"No response returned when trying to update field with label '{label}'")

        component = find_component_by_label_and_type_dict('testLabel', test_label, 'PickerWidget', new_state)

        suggestions_list = extract_all_by_label(component, 'suggestions')

        if not suggestions_list:
            raise Exception(f"No suggestions returned when '{value}' was entered in the picker field.")

        identifiers = extract_all_by_label(suggestions_list, 'identifier')

        if not identifiers:
            raise Exception(f"No identifiers found when '{value}' was entered in the picker field.")

        # Introspect to see if there's an ID
        index_by_id = identifiers[0].get('id') is not None
        id_index = 'id' if index_by_id else '#v'
        v_or_id = [identifier.get(id_index) for identifier in identifiers if identifier.get(id_index)]
        t = [identifier.get('#t') for identifier in identifiers]
        if not v_or_id:
            raise Exception(f"Could not extract picker values '{id_index}' from suggestions_list {suggestions_list}")
        v_choice = random.choice(range(len(v_or_id)))
        dict_value = {id_index: v_or_id[v_choice], "#t": t[v_choice]}

        locust_label = pick_request_label or f"{self.breadcrumb}.SelectPickerSuggestion.{label}"
        newer_state = self.interactor.select_pickerfield_suggestion(
            self.form_url, component, dict_value, self.context, self.uuid, label=locust_label)

        if not newer_state:
            raise Exception(f"No response returned when trying to update field with label '{label}'")

        return self._reconcile_and_produce_new_form(new_state)

    @raises_locust_error("uiform.py/click()")
    def click(self, label: str, is_test_label: bool = False, locust_request_label: str = "") -> 'SailUiForm':
        """
        Fills a field on the form, if there is one present with the following label (case sensitive)
        Otherwise throws a NotFoundException

        Args:
            label(str): Label of the component to click
            is_test_label(bool): If you are clicking a button or link via a test label instead of a label, set this boolean to true

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.click('Submit')
            >>> form.click('SampleTestLabel', is_test_label = True)

        """
        attribute_to_find = 'testLabel' if is_test_label else 'label'
        component = find_component_by_attribute_in_dict(
            attribute_to_find, label, self.state)
        self._validate_component_found(component, label)

        locust_label = locust_request_label or f"{self.breadcrumb}.Click.{label}"
        reeval_url = self._get_update_url_for_reeval(self.state)
        new_state = self.interactor.click_component(
            reeval_url, component, self.context, self.uuid, label=locust_label)

        if not new_state:
            raise Exception(f"No response returned when trying to click button with label '{label}'")
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    # Aliases for click() function
    click_button = click
    click_link = click

    @raises_locust_error("uiform.py/click_card_layout_by_index()")
    def click_card_layout_by_index(self, index: int, locust_request_label: str = "") -> 'SailUiForm':
        """
        Clicks a card layout link by index

        Args:
            index(int): Index of the card layout on which to click.

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.click_card_layout_by_index(2)

        """
        component = find_component_by_index_in_dict("CardLayout", index, self.state)
        # Add an arbitrary label to the cardlayout component to help with link clicking
        component["label"] = "CardLayoutLabel"
        locust_label = locust_request_label or f"{self.breadcrumb}.ClickCardLayout.Index.{index}"
        reeval_url = self._get_update_url_for_reeval(self.state)
        new_state = self.interactor.click_component(
            reeval_url, component, self.context, self.uuid, label=locust_label)

        if not new_state:
            raise Exception(f"No response returned when trying to click card layout at index '{index}'")
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/click_record_link()")
    def click_record_link(self, label: str, locust_request_label: str = "") -> 'SailUiForm':
        """
        Click a record link on the form if there is one present with the following label (case sensitive)
        Otherwise throws a ComponentNotFoundException

        Args:
            label(str): Label of the record link to click

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The record form (feed) for the linked record.

        """
        component = find_component_by_attribute_in_dict('label', label, self.state)
        self._validate_component_found(component, label)

        reeval_url = self._get_update_url_for_reeval(self.state)
        locust_label = locust_request_label or f"{self.breadcrumb}.ClickRecordLink.{label}"
        new_state = self.interactor.click_record_link(reeval_url, component, self.context, self.uuid,
                                                      locust_label=locust_label)
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/click_start_process_link()")
    def click_start_process_link(self, label: str, site_name: str, page_name: str, is_mobile: bool = False, locust_request_label: str = "") -> 'SailUiForm':
        """
        Clicks a start process link on the form by label
        If no link is found, throws a ComponentNotFoundException

        Args:
            label(str): Label of the link
            site_name(str): Name of the site (i.e. the Sites feature)
            page_name(str): Name of the page within the site

        Keyword Args:
            is_mobile(bool): Boolean to use the mobile form of the request
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:
            >>> form.click_start_process_link('Request upgrade')

        """

        component = find_component_by_label_and_type_dict('label', label, 'StartProcessLink', self.state)
        self._validate_component_found(component, label)

        process_model_opaque_id = component.get("processModelOpaqueId", "")
        cache_key = component.get("cacheKey", "")

        if not process_model_opaque_id or not cache_key:
            raise Exception(f'''
                            StartProcessLink component does not have process model opaque id or cache key set.
                            ''')
        locust_label = locust_request_label or f"{self.breadcrumb}.ClickStartProcessLink.{label}"
        new_state = self.interactor.click_start_process_link(label, component, process_model_opaque_id,
                                                             cache_key, site_name, page_name, is_mobile,
                                                             locust_request_label=locust_label)
        # get the re-eval URI from links object of the response (new_state)
        reeval_url = self._get_update_url_for_reeval(new_state)
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/click_start_process_link_on_mobile()")
    def click_start_process_link_on_mobile(self, label: str, site_name: str, page_name: str, locust_request_label: str = "") -> 'SailUiForm':
        """
        Clicks a start process link on the form by label (for Mobile)
        If no link is found, throws a ComponentNotFoundException

        Args:
            label(str): Label of the link
            site_name(str): Name of the site (i.e. the Sites feature)
            page_name(str): Name of the page within the site

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.click_start_process_link_on_mobile('Open Issue')

        """
        locust_label = locust_request_label or f"{self.breadcrumb}.ClickStartProcessLink.Mobile.{label}"
        return self.click_start_process_link(label, site_name, page_name, is_mobile=True, locust_request_label=locust_label)

    @raises_locust_error("uiform.py/click_related_action_link()")
    def click_related_action(self, label: str, locust_request_label: str = "") -> 'SailUiForm':
        """
        Clicks a related action (either a related action button or link) on the form by label
        If no link is found, throws a ComponentNotFoundException

        Args:
            label(str): Label of the related action

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:
            How to use click_related_action():
            Use records function - visit_record_instance_and_get_feed_form() to get Record Instance SailUiForm, then get the header response
            and finally click on the related action by label.

            >>> feed_form = records.visit_record_instance_and_get_feed_form()

            >>> header_form = feed_form.get_record_header_form()

            >>> header_form.click_related_action('Request upgrade')

        """
        component = find_component_by_attribute_in_dict('label', label, self.state)
        self._validate_component_found(component, label)
        # Support scenario where related action label is found within outer "ButtonWidget" rather than directly in "RelatedActionLink" component
        if "source" not in component:
            component = component.get("link", "")
        component_source = component.get("source", "")
        record_type_stub = component_source.get("recordTypeStub", "")
        opaque_record_id = component_source.get("opaqueRecordId", "")
        opaque_related_action_id = component_source.get("opaqueRelatedActionId", "")

        if not record_type_stub or not opaque_record_id or not opaque_related_action_id:
            raise Exception(f'''
                            Related Action link component does not have recordTypeStub or opaqueRecordId or opaqueRelatedActionId set.
                            ''')
        locust_label = locust_request_label or f"{self.breadcrumb}.ClickRelatedActionLink.{label}"

        new_state = self.interactor.click_related_action(component, record_type_stub, opaque_record_id,
                                                         opaque_related_action_id, locust_label)
        # get the re-eval URI from links object of the response (new_state)
        reeval_url = self._get_update_url_for_reeval(new_state)
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/select_dropdown_item()")
    def select_dropdown_item(self, label: str, choice_label: str, locust_request_label: str = "", is_test_label: bool = False) -> 'SailUiForm':
        """
        Selects a dropdown item on the form
        If no dropdown found, throws a NotFoundException
        If no element found, throws a ChoiceNotFoundException

        Args:
            label(str): Label of the dropdown
            choice_label(str): Label of the dropdown item to select
            is_test_label(bool): If you are interacting with a dropdown via a test label instead of a label, set this boolean to true.
                                 User filters on a record instance list use test labels.

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.select_dropdown_item('MyDropdown', 'My First Choice')

        """
        attribute_to_find = 'testLabel' if is_test_label else 'label'
        component = find_component_by_attribute_in_dict(
            attribute_to_find, label, self.state)

        self._validate_component_found(component, label)

        choices: list = component.get('choices')
        if not choices:
            raise InvalidComponentException(f"No choices found for component {label}, is the component a Dropdown?")
        if not isinstance(choice_label, list) and choice_label not in choices:
            raise ChoiceNotFoundException(f"Choice {choice_label} not found for component {label}, valid choices were {choices}")

        index = choices.index(choice_label) + 1  # Appian is _sigh_ one indexed

        locust_label = locust_request_label or f'{self.breadcrumb}.SelectDropdownWithLabel.{choice_label}'
        reeval_url = self._get_update_url_for_reeval(self.state)
        new_state = self.interactor.send_dropdown_update(
            reeval_url, component, self.context, self.uuid, index=index, label=locust_label)
        if not new_state:
            raise Exception(
                f"No response returned when trying to click button with label '{label}'")

        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    def _check_checkbox_by_attribute(self, attribute: str, value_for_attribute: str, indices: List[int], locust_request_label: str = "") -> 'SailUiForm':
        """
        Function that checks checkboxes.
        It finds checkboxes by the attribute and its value provided.

        Args:
            attribute(str): attribute to use to find the checkbox
            value_for_attribute(str): Value of the attribute used to find the checkbox
            indices(str): Indices of the checkbox to check. Pass None or empty to uncheck all

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm
        """
        component = find_component_by_attribute_in_dict(attribute, value_for_attribute, self.state)

        self._validate_component_found_by_attribute(component, attribute, value_for_attribute)

        locust_label = locust_request_label or f'{self.breadcrumb}.CheckCheckboxByAttribute.{attribute}'
        reeval_url = self._get_update_url_for_reeval(self.state)
        new_state = self.interactor.select_checkbox_item(
            reeval_url, component, self.context, self.uuid, indices=indices, context_label=locust_label)
        if not new_state:
            raise Exception(f'''No response returned when trying to check checkbox which was found with attribute: '{attribute}'
                            and its value: '{value_for_attribute}' on the current page
                            ''')

        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/check_checkbox_by_test_label()")
    def check_checkbox_by_test_label(self, test_label: str, indices: List[int], locust_request_label: str = "") -> 'SailUiForm':
        """
        Checks a checkbox by its testLabel attribute
        Indices are positions to be checked

        Args:
            test_label(str): Value for the testLabel attribute of the checkbox
            indices(str): Indices of the checkbox to check. Pass None or empty to uncheck all

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.check_checkbox_by_test_label('myTestLabel', [1])  # checks the first item
            >>> form.check_checkbox_by_test_label('myTestLabel', None) # unchecks

        """
        if not test_label:
            raise Exception(f"No testLabel provided to select a checkbox")

        locust_label = locust_request_label or f'{self.breadcrumb}.CheckCheckboxByTestLabel.{test_label}'
        return self._check_checkbox_by_attribute('testLabel', test_label, indices, locust_request_label=locust_label)

    @raises_locust_error("uiform.py/check_checkbox_by_label()")
    def check_checkbox_by_label(self, label: str, indices: List[int], locust_request_label: str = "") -> 'SailUiForm':
        """
        Checks a checkbox by its label
        Indices are positions to be checked

        Args:
            label(str): Value for label of the checkbox
            indices(str): Indices of the checkbox to check. Pass None or empty to uncheck all

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.check_checkbox_by_label('myLabel', [1])  # checks the first item
            >>> form.check_checkbox_by_label('myLabel', None) # unchecks

        """
        if not label:
            raise Exception(f"No label provided to select a checkbox")

        locust_label = locust_request_label or f'{self.breadcrumb}.CheckCheckboxByLabel.{label}'
        return self._check_checkbox_by_attribute('label', label, indices, locust_request_label=locust_label)

    @raises_locust_error("uiform.py/click_tab_by_label()")
    def click_tab_by_label(self, tab_label: str, tab_group_test_label: str, locust_request_label: str = "") -> 'SailUiForm':
        """
        Selects a Tab by its label and its tab group's testLabel

        Args:
            tab_label(str): Label of the tab to select
            tab_group_test_label(str): Test Label of the tab group (tab is part of a tab group)

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

        """
        # find the TabButtonGroup, which is the  model we need for the SaveRequest
        reeval_url = self._get_update_url_for_reeval(self.state)

        tab_group_component = find_component_by_attribute_in_dict('testLabel', tab_group_test_label, self.state)
        self._validate_component_found(tab_group_component, tab_group_test_label)
        new_state = self.interactor.click_selected_tab(
            reeval_url, tab_group_component, tab_label, self.context, self.uuid)
        if not new_state:
            raise Exception(
                f'''No response returned when trying to click a tab with label: '{tab_label}'
                inside the TabButtonGroup component with testLabel: '{tab_group_test_label}'''
            )

        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/upload_document_to_upload_field()")
    def upload_document_to_upload_field(self, label: str, file_path: str, locust_request_label: str = "") -> 'SailUiForm':
        """
        Uploads a document to a named upload field
        There are two steps to this which can fail, one is the document upload, the other
        is finding the component and applying the update.

        Args:
            label(str): Label of the upload field
            file_path(str): File path to the document

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.upload_document_to_upload_field('Upload File', "/usr/local/appian/File.zip")
            >>> form.upload_document_to_upload_field('Upload Properties', "/usr/local/appian/File.properties")

        """
        component = find_component_by_attribute_in_dict(
            'label', label, self.state)

        self._validate_component_found(component, label)

        # Inner component can be the upload field
        if component.get('#t') != 'FileUploadWidget' and 'contents' in component:
            component = component['contents']

        # Check again to see if the wrong component
        if component.get('#t') != 'FileUploadWidget':
            raise Exception(f"Provided component was not a FileUploadWidget, was instead of type '{component.get('#t')}'")

        is_encrypted = component.get("isEncrypted", False)

        if not os.path.exists(file_path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        doc_id = self.interactor.upload_document_to_server(file_path, is_encrypted=is_encrypted)
        locust_label = locust_request_label or f"{self.breadcrumb}.FileUpload.{label}"
        new_state = self.interactor.upload_document_to_field(
            self.form_url, component, self.context, self.uuid, doc_id=doc_id, locust_label=locust_label)
        if not new_state:
            raise Exception(
                f"No response returned when trying to upload file to field '{label}'")
        return self._reconcile_and_produce_new_form(new_state)

    @raises_locust_error("uiform.py/move_to_end_of_paging_grid()")
    def move_to_end_of_paging_grid(self, label: str = None, index: int = None, locust_request_label: str = "") -> 'SailUiForm':
        """
        Moves to the end of a paging grid, if possible
        Either a label or an index is required, indices are useful if there is no title for the grid

        Args:
            label(str): Label of the grid
            index(str): Index of the grid

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.move_to_end_of_paging_grid(label='my nice grid')
        """
        grid = self.grid_interactor.find_grid_by_label_or_index(self.state, label=label, index=index)
        grid_label = self.grid_interactor.format_grid_display_label(grid)

        new_grid_save = self.grid_interactor.move_to_last_page(grid)
        context_label = locust_request_label or f"{self.breadcrumb}.Grid.MoveToEnd.{grid_label}"

        reeval_url = self._get_update_url_for_reeval(self.state)
        new_state = self.interactor.update_grid_from_sail_form(reeval_url, grid, new_grid_save,
                                                               self.context, self.uuid, context_label=context_label)
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/move_to_beginning_of_paging_grid()")
    def move_to_beginning_of_paging_grid(self, label: str = None, index: int = None, locust_request_label: str = "") -> 'SailUiForm':
        """
        Moves to the beginning of a paging grid, if possible
        Either a label or an index is required, indices are useful if there is no title for the grid

        Args:
            label(str): Label of the grid
            index(str): Index of the grid

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.move_to_beginning_of_paging_grid(label='my nice grid')
        """
        grid = self.grid_interactor.find_grid_by_label_or_index(self.state, label=label, index=index)
        grid_label = self.grid_interactor.format_grid_display_label(grid)

        new_grid_save = self.grid_interactor.move_to_first_page(grid)
        context_label = locust_request_label or f"{self.breadcrumb}.Grid.MoveToBeginning.{grid_label}"

        reeval_url = self._get_update_url_for_reeval(self.state)
        new_state = self.interactor.update_grid_from_sail_form(reeval_url, grid, new_grid_save,
                                                               self.context, self.uuid, context_label=context_label)
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/move_to_left_in_paging_grid()")
    def move_to_left_in_paging_grid(self, label: str = None, index: int = None, locust_request_label: str = "") -> 'SailUiForm':
        """
        Moves to the left in a paging grid, if possible
        It might require getting the state of the grid if you've moved to the end/ previous part of the grid
        Either a label or an index is required, indices are useful if there is no title for the grid

        Args:
            label(str): Label of the grid
            index(str): Index of the grid

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.move_to_left_in_paging_grid(label='my nice grid')
        """
        grid = self.grid_interactor.find_grid_by_label_or_index(self.state, label=label, index=index)
        grid_label = self.grid_interactor.format_grid_display_label(grid)

        new_grid_save = self.grid_interactor.move_to_the_left(grid)
        context_label = locust_request_label or f"{self.breadcrumb}.Grid.MoveLeft.{grid_label}"

        reeval_url = self._get_update_url_for_reeval(self.state)
        new_state = self.interactor.update_grid_from_sail_form(reeval_url, grid, new_grid_save,
                                                               self.context, self.uuid, context_label=context_label)
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/move_to_right_in_paging_grid()")
    def move_to_right_in_paging_grid(self, label: str = None, index: int = None, locust_request_label: str = "") -> 'SailUiForm':
        """
        Moves to the right in a paging grid, if possible
        It might require getting the state of the grid if you've moved within the grid
        Either a label or an index is required, indices are useful if there is no title for the grid

        Args:
            label(str): Label of the grid
            index(str): Index of the grid

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.move_to_right_in_paging_grid(index=0) # move to right in first grid on the page
        """
        grid = self.grid_interactor.find_grid_by_label_or_index(self.state, label=label, index=index)
        grid_label = self.grid_interactor.format_grid_display_label(grid)

        new_grid_save = self.grid_interactor.move_to_the_right(grid)
        context_label = locust_request_label or f"{self.breadcrumb}.Grid.MoveRight.{grid_label}"

        reeval_url = self._get_update_url_for_reeval(self.state)
        new_state = self.interactor.update_grid_from_sail_form(reeval_url, grid, new_grid_save,
                                                               self.context, self.uuid, context_label=context_label)
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/sort_paging_grid()")
    def sort_paging_grid(self, label: str = None, index: int = None, field_name: str = "", ascending: bool = False, locust_request_label: str = "") -> 'SailUiForm':
        """
        Sorts a paging grid by the field name, which is not necessarily the same as the label of the column
        And might require inspecting the JSON to determine what the sort field is

        Sorts by ascending = False by default, override to set it to True

        Either a label or an index is required, indices are useful if there is no title for the grid

        Args:
            label(str): Label of the grid
            index(str): Index of the grid
            field_name(str): Field to sort on (not necessarily the same as the displayed one)
            ascending(bool): Whether to sort ascending, default is false

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.sort_paging_grid(index=0,field_name='Total',ascending=True)
        """
        if not field_name:
            raise Exception("Field to sort cannot be blank when sorting a grid")
        grid = self.grid_interactor.find_grid_by_label_or_index(self.state, label=label, index=index)
        grid_label = self.grid_interactor.format_grid_display_label(grid)

        new_grid_save = self.grid_interactor.sort_grid(field_name=field_name, paging_grid=grid, ascending=ascending)
        context_label = locust_request_label or f"{self.breadcrumb}.Grid.Sort.{grid_label}.{field_name}"

        reeval_url = self._get_update_url_for_reeval(self.state)
        new_state = self.interactor.update_grid_from_sail_form(reeval_url, grid, new_grid_save,
                                                               self.context, self.uuid, context_label=context_label)
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/select_radio_button_by_test_label()")
    def select_radio_button_by_test_label(self, test_label: str, index: int, locust_request_label: str = "") -> 'SailUiForm':
        """
        Selects a radio button by its test label
        Index is position to be selected

        Args:
            test_label(str): Label of the radio button field
            index(int): Index of the radio button to select

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.select_radio_button_by_test_label('myTestLabel', 1)  # selects the first item

        """
        component = find_component_by_attribute_in_dict(
            'testLabel', test_label, self.state)

        self._validate_component_found(component, test_label)

        reeval_url = self._get_update_url_for_reeval(self.state)
        context_label = locust_request_label or f"{self.breadcrumb}.RadioButton.SelectByTestLabel.{test_label}"
        new_state = self.interactor.select_radio_button(
            reeval_url, component, self.context, self.uuid, index=index, context_label=context_label)
        if not new_state:
            raise Exception(
                f"No response returned when trying to select radio button with testLabel '{test_label}'")
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/select_radio_button_by_label()")
    def select_radio_button_by_label(self, label: str, index: int, locust_request_label: str = "") -> 'SailUiForm':
        """
        Selects a radio button by its label
        Index is position to be selected

        Args:
            label(str): Label of the radio button field
            index(int): Index of the radio button to select

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.select_radio_button_by_label('myLabel', 1)  # selects the first item

        """
        component = find_component_by_attribute_in_dict(
            'label', label, self.state)

        self._validate_component_found(component, label)

        reeval_url = self._get_update_url_for_reeval(self.state)
        context_label = locust_request_label or f"{self.breadcrumb}.RadioButton.SelectByLabel.{label}"
        new_state = self.interactor.select_radio_button(
            reeval_url, component, self.context, self.uuid, index=index, context_label=context_label)
        if not new_state:
            raise Exception(
                f"No response returned when trying to select radio button with label '{label}'")
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    @raises_locust_error("uiform.py/select_radio_button_by_index()")
    def select_radio_button_by_index(self, field_index: int, index: int, locust_request_label: str = "") -> 'SailUiForm':
        """
        Selects a radio button by its field index
        Index is position to be selected

        Args:
            field_index(int): Index of the radio button field on the page
            index(int): Index of the radio button to select

        Keyword Args:
            locust_request_label(str): Label used to identify the request for locust statistics

        Returns (SailUiForm): The latest state of the UiForm

        Examples:

            >>> form.select_radio_button_by_index(1, 1)  # selects the first item in the first radio button field

        """
        component = find_component_by_index_in_dict(
            'RadioButtonField', field_index, self.state)

        reeval_url = self._get_update_url_for_reeval(self.state)
        context_label = locust_request_label or f"{self.breadcrumb}.RadioButton.SelectByIndex.{index}"
        new_state = self.interactor.select_radio_button(
            reeval_url, component, self.context, self.uuid, index=index, context_label=context_label)
        if not new_state:
            raise Exception(
                f"No response returned when trying to select radio button with index '{field_index}'")
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    def go_to_next_record_grid_page(self, locust_request_label: str = "") -> 'SailUiForm':
        context_label = locust_request_label or f"{self.breadcrumb}.NextPage"
        headers = self.interactor.setup_request_headers()
        headers["Accept"] = "application/vnd.appian.tv.ui+json"
        reeval_url = self._get_update_url_for_reeval(self.state)
        label = 'NEXT'
        if not _is_grid(self.state):
            raise Exception("Not a grid record list")
        component = find_component_by_attribute_in_dict(
            'label', label, self.state)
        new_state = self.interactor.interact_with_record_grid(
            post_url=reeval_url, grid_component=component, context=self.context, uuid=self.uuid, context_label=context_label)
        if not new_state:
            raise Exception(
                f"No response returned when navigating to next page on record list '{reeval_url}'")
        return self._reconcile_and_produce_new_form(new_state, form_url=reeval_url)

    def get_record_header_form(self) -> 'SailUiForm':
        """
        Extracts the embedded record header form from a record "feed" form to enable interaction with components in the record header.

        Returns (SailUiForm): The record header UiForm embedded within a record "feed" form.

        Examples:

            >>> form.get_record_header_form()

        """
        # self in this case is a record form (feed) containing embedded forms (header and view form)
        record_header_response = get_record_header_response(self.state)

        # record "feed" form has no breadcrumb - set up a breadcrumb
        self.breadcrumb = "Record.HeaderForm.SailUi"

        return SailUiForm(self.interactor, json.loads(record_header_response), self.form_url,
                          breadcrumb=self.breadcrumb)

    def get_record_view_form(self) -> 'SailUiForm':
        """
        Extracts the embedded record view form from a record "feed" form to enable interaction with components in the record view.

        Returns (SailUiForm): The record view UiForm embedded within a record "feed" form.

        Examples:

            >>> form.get_record_view_form()

        """
        record_view_response = get_record_summary_view_response(self.state)

        # record "feed" form has no breadcrumb - set up a breadcrumb
        self.breadcrumb = "Record.ViewForm.SailUi"

        return SailUiForm(self.interactor, json.loads(record_view_response), self.form_url, breadcrumb=self.breadcrumb)

    def filter_records_using_searchbox(self, search_term: str = "", locust_request_label: str = "") -> 'SailUiForm':
        """
        This method allows you to Filter the Record Type List (displaying record instance for a specific record type)
        which makes the same request when typing something in the search box and reloading the page.
        More interactions (with the filtered list) can be performed on the returned SailUiForm Object.

        Note: This is different from how an end user interacts with the SearchBox. In that case you would type something in the box
        and when you would unfocus from the box a reevaluation happens and then you click the 'Search' button which returns the filtered
        results.

        Examples:

            >>> form.filter_records_using_searchbox('Donuts')

        Returns (SailUiForm): The record type list UiForm with the filtered results.
        """
        context_label = locust_request_label or f"{self.breadcrumb}.RecordType.SearchByText"
        search_uri = f"{self.form_url}?searchTerm={quote(search_term)}"

        headers = self.interactor.setup_sail_headers()
        response = self.interactor.get_page(uri=search_uri, headers=headers, label=context_label)
        return SailUiForm(self.interactor, response.json(), self.form_url, breadcrumb=context_label)

    def assert_no_validations_present(self) -> 'SailUiForm':
        """
        Raises an exception if there are validations present on the form, otherwise, returns the form as is

        Returns (SailUiForm): Form as it was when validations were asserted
        """
        validations: list = extract_all_by_label(self.state, "validations")
        validation_present = False
        for validation in validations:
            if validation:
                log.error(f'Validations were found in the form {self.breadcrumb}, validation: {validation}')
                validation_present = True
        if validation_present:
            raise Exception(f"At least one validation was found in the form {self.breadcrumb}")
        return self

    def _reconcile_and_produce_new_form(self, new_state: dict, form_url: str = "") -> 'SailUiForm':
        self.interactor.datatype_cache.cache(new_state)  # Also update datatypes cache
        reconciled_state = self.reconciler.reconcile_ui(self.state, new_state)
        new_form_url = form_url if form_url else self.form_url
        return SailUiForm(self.interactor, reconciled_state, new_form_url, breadcrumb=self.breadcrumb)

    def _validate_component_found(self, component: Optional[Dict[str, Any]], label: str) -> None:
        if not component:
            raise ComponentNotFoundException(
                f"Could not find the component with label '{label}' in the provided form"
            )

    def _validate_component_found_by_attribute(self, component: Dict[str, Any], attribute: str, value_for_attribute: str) -> None:
        if not component:
            raise ComponentNotFoundException(
                f'''Could not find the component with attribute '{attribute}' and
                its value: '{value_for_attribute}' in the provided form
                ''')

    def _get_update_url_for_reeval(self, state: Dict[str, Any]) -> str:
        """
        This function looks at the links object in a SAIL response
        and finds the URL for "rel"="update", which is then used to do other
        interactions on the form.
        """

        # get the re-eval URI from links object of the response (new_state)
        list_of_links = state["links"]
        reeval_url = self.form_url
        for link_object in list_of_links:
            if link_object.get("rel") == "update":
                reeval_url = urlparse(link_object.get("href", "")).path
                break
        return reeval_url


class ComponentNotFoundException(Exception):
    pass


class InvalidComponentException(Exception):
    pass


class ChoiceNotFoundException(Exception):
    pass

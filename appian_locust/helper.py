import functools
import random
import re
from typing import Any, Callable, Dict, Generator, List, Union

import gevent  # type: ignore
from locust.env import Environment

from . import logger

ENV = Environment()
log = logger.getLogger(__name__)


def format_label(label: str, delimiter: str = None, index: int = 0) -> str:
    """
    Simply formats the string by replacing a space with underscores

    Args:
        label: string to be formatted
        delimiter: If provided, string will be split by it
        index: used with delimiter parameter, which item will be used in the "split"ed list.

    Returns:
        formatted string

    """
    if delimiter:
        if not str(index).isnumeric():
            index = 0
        label = label.split(delimiter)[int(index)]

    return label.replace(" ", "_")


def extract(obj: Any, key: str, val: Any) -> Generator:
    """Recursively search for values of key in JSON tree."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                yield from extract(v, key, val)
            elif k == key and v == val:
                yield obj

    elif isinstance(obj, list):
        for item in obj:
            yield from extract(item, key, val)


def extract_values(obj: Dict[str, Any], key: str, val: Any) -> List[Dict[str, Any]]:
    """
    Pull all values of specified key from nested JSON.

    Args:
        obj (dict): Dictionary to be searched
        key (str): tuple of key and value.
        value (any): value, which can be any type

    Returns:
        list of matched key-value pairs

    """
    return [elem for elem in extract(obj, key, val)]


def extract_item_by_label(obj: Union[dict, list], label: str) -> Generator:
    """
    Recursively search for all fields with a matching label in JSON tree.
    And return as a generator
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == label:
                yield v
            yield from extract_item_by_label(v, label)
    elif isinstance(obj, list):
        for v in obj:
            yield from extract_item_by_label(v, label)


def extract_all_by_label(obj: Union[dict, list], label: str) -> list:
    """Recursively search for all fields with a matching label in JSON tree."""
    return [elem for elem in extract_item_by_label(obj, label)]


def get_random_item(list_of_items: List[Any], exclude: List[Any] = []) -> Any:
    """
    Gets a random item from the given list excluding the items if any provided

    Args:
        list_of_items: list of items of any data type
        exclude: if any items needs to be excluded in random pick

    Returns:
        Randomly picked Item

    Raises:
        In case of no item to pick, Exception will be raised
    """
    count = len(list_of_items)
    while count != 0:
        selected_item = random.SystemRandom().choice(list_of_items)
        if selected_item not in exclude:
            return selected_item
        else:
            count = count - 1
    raise(Exception("There is no item to select randomly"))


def list_filter(list_var: List[str], filter_string: str, exact_match: bool = False) -> List[str]:
    """
    from the given list, return the list with filtered values.

    Args:
        list_var (list): list of strings
        filter_string (str): string which will be used to filter
        exact_match (bool, optional): filter should be based on exact match or partial match. default is partial.

    Returns:
        List with filtered values

    """
    # Exact Matches gets priority even when exact match is set to false
    return_list = list(filter(lambda current_item: (
        current_item == filter_string), list_var))
    if not exact_match:
        return_list = list(filter(lambda current_item: (
            current_item == filter_string), list_var))
        return_list.extend(list(filter(lambda current_item: (
            bool(re.search(".*" + re.escape(filter_string) + ".*", current_item)) and current_item not in return_list),
            list_var)))
    return return_list


def find_component_by_attribute_in_dict(attribute: str, value: str, component_tree: Dict[str, Any]) -> Any:
    """
    Find a UI component by the given attribute (label for example) in a dictionary
    It only returns the first match in a depth first search of the json tree
    It returns the dictionary that contains the given attribute with the given value
    or returns None when not found

    Args:
        attribute: an attribute to search ('label' for example)
        value: the value of the attribute ('Submit' for example)
        component_tree: the json response.

    Returns:
        the json object of the component or None if none is found

    Example:
        >>> find_component_by_attribute_in_dict('label', 'Submit', self.json_response)

        will search the json response to find a component that has 'Submit' as the label

    """
    for val in extract(component_tree, attribute, value):
        return val


def find_component_by_label_and_type_dict(attribute: str, value: str, type: str, component_tree: Dict[str, Any]) -> Any:
    """
    Find a UI component by the given attribute (like label) in a dictionary, and the type of the component as well.
    (`#t` should match the type value passed in)
    It only returns the first match in a depth first search of the json tree.
    It returns the dictionary that contains the given attribute with the given label and type
    or returns None when not found.

    Args:
        label: label of the component to search
        value: the value of the label
        type: Type of the component (TextField, StartProcessLink etc.)
        component_tree: the json response.

    Returns:
        the json object of the component or None if none is found

    Example:
        >>> find_component_by_label_and_type_dict('label', 'MyLabel', 'StartProcessLink', self.json_response)

    """
    for val in extract(component_tree, attribute, value):
        if (('#t' in val) and (val['#t'] == type)):
            return val


def find_component_by_index_in_dict(component_type: str, index: int, component_tree: Dict[str, Any]) -> Any:
    """
    Find a UI component by the index of a given type of component ("RadioButtonField" for example) in a dictionary
    Performs a depth first search and counts quantity of the component, so the 1st is the first one
    It returns the dictionary that contains the given attribute with the requested index
    or returns the total number of components with that attribute when the index could not be matched

    Args:
        component_type: type of the component(#t in the JSON response, 'RadioButtonField' for example)
        index: the index of the component with the component_type ('1' for example - Indices start from 1)
        component_tree: the json response

    Returns:
        the json object of the component or the count of matching attributes if no match found

    Example:
        >>> find_component_by_index_in_dict('RadioButtonField', 1, self.json_response)

        will search the json response to find the first component that has 'RadioButtonField' as the type

    """
    if (not isinstance(index, int)) or index <= 0:
        raise Exception(
            f"Invalid index: '{index}'.  Please enter a positive number")

    result = _find_component_by_type_and_index(component_type, index, component_tree, 0)

    if isinstance(result, int):
        if result == 0:
            raise Exception(f"No components of type '{component_type}' found on page")
        else:
            raise Exception(f"Bad index: only '{result}' components of type '{component_type}' found on page, " +
                            f"requested '{index}'")

    return result


def _find_component_by_type_and_index(type_name: str, index: int, component: Any, count: int) -> Any:
    is_dict = isinstance(component, dict)
    if is_dict:
        if '#t' in component and component.get('#t') == type_name:
            count += 1
            if count == index:
                return component
    if is_dict or isinstance(component, list):
        component_items = component.values() if is_dict else component
        for inner_component in component_items:
            if isinstance(inner_component, (dict, list)):
                result = _find_component_by_type_and_index(type_name, index, inner_component, count)
                if isinstance(result, dict):
                    return result
                else:
                    count = result
    return count


def repeat(num_times: int = 2, wait_time: float = 0.0) -> Callable:
    """
    This function allows an arbitrary function to be executed an arbitrary number of times
    The intended use is as a decorator:

    >>> @repeat(2)
    ... def arbitrary_function():
    ...     print("Hello World")
    ... arbitrary_function()
    Hello World
    Hello World

    Args:
        num_times (int): an integer

    Implicit Args:
        arbitrary_function (Callable): a python function

    Returns:
        A reference to a function which performs the decorated function num_times times

    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper_decorator(*args: Any, **kwargs: Any) -> Any:
            for _ in range(num_times):
                value = func(*args, **kwargs)
                gevent.sleep(wait_time)
            return value
        return wrapper_decorator
    return decorator


def get_username(auth: list) -> str:
    if auth and len(auth) >= 1 and auth[0]:
        return auth[0]
    else:
        return ""

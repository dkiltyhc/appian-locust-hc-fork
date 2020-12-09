import json
import time
import unittest
from typing import List

from appian_locust.helper import (find_component_by_attribute_in_dict,
                                  find_component_by_label_and_type_dict,
                                  repeat)

from .mock_reader import read_mock_file


class TestHelper(unittest.TestCase):
    form_dict = json.loads(read_mock_file("test_response.json"))

    def test_find_component_by_label_and_type(self) -> None:
        component = find_component_by_label_and_type_dict('label', 'Log Contacts', 'StartProcessLink', self.form_dict)
        # finds first component with that label and type
        self.assertEqual(component['cacheKey'], '3ba597c4-1eaf-42ef-947a-698397169f9c')
        self.assertEqual(component['processModelOpaqueId'], 'iMB8GmxIr5iZT6YnVyo69ieCl0Uw2I5NY9p4g4W9_3ZRs-8MA')

    def test_find_component_by_attribute_in_dict(self) -> None:
        component = find_component_by_attribute_in_dict('label', 'Log Contacts', self.form_dict)
        # finds first component by that label
        self.assertEqual(component['#t'], 'RichTextDisplayField')

    def test_repeat_decorator(self) -> None:
        # Given
        my_list: List[int] = []

        @repeat(2)
        def append_one(my_list: List) -> None:
            my_list.append(1)
        # When
        append_one(my_list)
        # Then
        self.assertEqual([1, 1], my_list)

    def test_repeat_decorator_naked(self) -> None:
        # Given
        my_list: List[int] = []

        @repeat()
        def append_one(my_list: List) -> None:
            my_list.append(1)
        # When
        append_one(my_list)
        # Then
        self.assertEqual([1, 1], my_list)

    def test_repeat_decorator_sleeping(self) -> None:
        # Given
        my_list: List[int] = []
        wait_time = 0.1
        start = time.time()

        @repeat(wait_time=wait_time)
        def append_one(my_list: List) -> None:
            my_list.append(1)
        # When
        append_one(my_list)
        # Then
        self.assertLessEqual(2*wait_time, time.time() - start)
        self.assertGreaterEqual(2*wait_time+0.01, time.time() - start)

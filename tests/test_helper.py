import unittest
import time
from typing import List

from appian_locust.helper import repeat


class TestHelper(unittest.TestCase):

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

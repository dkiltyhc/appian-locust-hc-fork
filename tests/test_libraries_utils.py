import json
import os
from .mock_client import CustomLocust, SampleAppianTaskSequence
from .mock_reader import read_mock_file
import appian_locust.helper as helper

import unittest


class TestLibraryHelper(unittest.TestCase):

    def test_format_label(self) -> None:
        var = helper.format_label("first second")
        self.assertEqual(var, "first_second")

    def test_get_random_item(self) -> None:
        testlist = [10, 5, 6, 8, 2, 4]
        var = helper.get_random_item(testlist)
        self.assertIn(var, testlist)

    def test_get_random_item_with_exclude(self) -> None:
        testlist = [10, 5, 6, 8, 2, 4]
        exclude = [2, 4]
        var = helper.get_random_item(testlist, exclude)
        self.assertTrue((var in testlist and var not in exclude))

    def test_get_random_item_with_no_item_to_choose(self) -> None:
        testlist = [2]
        exclude = [2]
        with self.assertRaisesRegex(Exception, "There is no item to select randomly"):
            helper.get_random_item(testlist, exclude)

    def test_find_component_by_attribute_in_dict(self) -> None:
        dir_path = os.path.dirname(os.path.realpath(__file__))

        raw_data = read_mock_file("library_utils.json")
        testdata = json.loads(raw_data)

        output = helper.find_component_by_attribute_in_dict('step2_status', 'pass', testdata)
        self.assertTrue(output["step2_status"] == "pass")


if __name__ == '__main__':
    unittest.main()

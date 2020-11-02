from appian_locust import loadDriverUtils
import os
import unittest


class TestUtils(unittest.TestCase):

    def setUp(self) -> None:
        self.util = loadDriverUtils.utils

    def test_loadconfig(self) -> None:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        output = self.util.load_config(
            os.path.join(dir_path, "test_config.json"))
        self.assertEqual(output['auth'], ["username", "password"])

    def test_loadconfig_missing_file(self) -> None:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with self.assertRaises(SystemExit):
            missing_file_path = os.path.join(dir_path, "missing_config.json")
            self.util.load_config(missing_file_path)


if __name__ == '__main__':
    unittest.main()

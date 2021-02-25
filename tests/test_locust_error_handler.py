import unittest

import locust
from appian_locust._locust_error_handler import log_locust_error
from appian_locust.helper import ENV


class TestLocustErrorHandler(unittest.TestCase):

    def test_obtain_correct_location(self) -> None:
        ENV.stats.errors.clear()

        def run_with_error() -> None:
            e = Exception("abc")
            log_locust_error(e, raise_error=False)
        run_with_error()

        self.assertEqual(1, len(ENV.stats.errors))

        # Assert error structure
        error: locust.stats.StatsError = list(ENV.stats.errors.values())[0]
        self.assertEqual('DESC: No description', error.method)
        self.assertEqual('LOCATION: test_locust_error_handler.py/run_with_error()', error.name)
        self.assertEqual('EXCEPTION: abc', error.error)
        self.assertEqual(1, error.occurrences)


if __name__ == '__main__':
    unittest.main()

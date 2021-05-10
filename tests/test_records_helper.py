import json
import time
import unittest
from typing import List

from appian_locust.records_helper import (get_url_stub_from_record_list_url_path,
                                          get_url_stub_from_record_list_post_request_url)


class TestHelper(unittest.TestCase):
    def test_get_url_stub_of_record_list_from_expected_state(self) -> None:
        self.assertEqual(get_url_stub_from_record_list_url_path('tempo/records/type/url_stub123/view/all'), 'url_stub123')

    def test_get_url_stub_of_record_list_from_no_url(self) -> None:
        self.assertIsNone(get_url_stub_from_record_list_url_path(None))

    def test_get_url_stub_of_record_list_from_unexpected_url(self) -> None:
        self.assertIsNone(get_url_stub_from_record_list_url_path('tempo/reports/view/url_stub123/view/all'))

    def test_get_url_stub_from_record_list_post_request_url_from_record_instance_list_url(self) -> None:
        # Given a record instance list url
        record_instance_list_url = '/suite/rest/a/sites/latest/D6JMim/pages/records/recordType/1vM_9A'

        # Attempt to get url stub
        record_instance_list_url_stub = get_url_stub_from_record_list_post_request_url(record_instance_list_url)

        # Then the record instance list url has its stub returned
        self.assertEqual(record_instance_list_url_stub, '1vM_9A')

    def test_get_url_stub_from_record_list_post_request_url_from_record_type_list_url(self) -> None:
        # Given a record type list url
        record_type_list_url = '/suite/rest/a/applications/latest/legacy/sites/D6JMim/page/records'

        # Attempt to get url stub
        record_type_list_url_stub = get_url_stub_from_record_list_post_request_url(record_type_list_url)

        # Then None is returned
        self.assertIsNone(record_type_list_url_stub)

    def test_get_url_stub_from_record_list_post_request_url_from_record_instance_url(self) -> None:
        # Given a record instance url
        record_instance_url = '/suite/rest/a/sites/latest/D6JMim/page/records/record/lQBU8YV4nEFVwMuczMM/view/summary'

        # Attempt to get url stub
        record_instance_url_stub = get_url_stub_from_record_list_post_request_url(record_instance_url)

        # Then None is returned
        self.assertIsNone(record_instance_url_stub)


if __name__ == '__main__':
    unittest.main()

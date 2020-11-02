#!/usr/bin/env python3

import sys
import random

from locust import HttpUser, task, between

from appian_locust import AppianTaskSet
from appian_locust.loadDriverUtils import utls
from appian_locust import logger

utls.load_config()
CONFIG = utls.c

logger = logger.getLogger(__file__)


class RecordsTaskSet(AppianTaskSet):

    def on_start(self):
        super().on_start()
        self.all_records = self.appian.records.get_all()

        # could be either view or list:
        if "endpoint_type" not in CONFIG:	 # could be either view or list:
            logger.error("endpoint_type not found in config.json")
            sys.exit(1)

        self.endpoint_type = CONFIG["endpoint_type"]

        if "view" not in self.endpoint_type and "list" not in self.endpoint_type:
            logger.error(
                "This behavior is not defined for the provided endpoint type. Supported types are : view and list")
            sys.exit(1)
        # view = to view records from opaqueId
        # list = to list all the record types from url_stub

    def on_stop(self):
        logger.info("logging out")
        super().on_stop()

    @task(10)
    def visit_random_record(self):
        if "view" in self.endpoint_type:
            dashboards = self._request_record_dashboards(
                random.choice((True, False)))
            for url_stub in dashboards:
                self.appian.records.visit(
                    view_url_stub=url_stub,
                    exact_match=True)

    @task(10)
    def visit_random_record_type_list(self):
        if "list" in self.endpoint_type:
            self.appian.records.visit_record_type()

    @task(1)
    def visit_random_record_and_get_form(self):
        if "view" in self.endpoint_type:
            record_type = random.choice((
                self.appian.records._get_random_record_type(), ""))
            self.appian.records.visit_record_instance_and_get_form(
                record_type=record_type)

    @task(1)
    def visit_random_record_type_list_and_get_form(self):
        if "list" in self.endpoint_type:
            self.appian.records.visit_record_type_and_get_form()

    def _request_record_dashboards(self, default_dashboard):
        if default_dashboard or "view_url_stubs" not in CONFIG:
            return [""]
        return CONFIG["view_url_stubs"]


class RecordsUserActor(HttpUser):
    tasks = [RecordsTaskSet]

    # These determine how long each user waits between @task runs.
    # A random wait time will be chosen between min_wait and max_wait
    # for each task run, ie this script has no waiting by default.
    wait_time = between(0.500, 0.500)

    host = "https://" + utls.c["site_name"] + "." + \
        utls.c.get("cluster_domain", "appiancloud.com")
    auth = utls.c["auth"]
    config = utls.c

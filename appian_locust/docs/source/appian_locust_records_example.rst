############################
Locust Test Example: Records
############################

An example of a Locust Test showing interaction with Appian Records - `example_locust_test_records.py <https://gitlab.com/appian-oss/appian-locust/-/blob/master/example_locustfile.py>`_.

This test has 3 locust tasks defined and it will execute all three for each spawned locust user for the duration of the test.

    - Task 1 will visit a random record type list.
    - Task 2 will visit a random record instance for a random record type and return the SAIL form.
    - Task 3 will visit a random record type list and get the SAIL form for it.

@task takes an optional weight argument that can be used to specify the task’s execution ratio.
For example: If there are two tasks with weights 3 and 6 then second task will have twice the chance of being picked as first task.

.. code-block:: python

    # Locust tests executing against Appian with a TaskSet should set AppianTaskSet as their base class to have access to various functionality.
    # This class handles creation of basic objects like `self.appian` (appian client) and actions like `login` and `logout`
    class RecordsTaskSet(AppianTaskSet):

    def on_start(self):
        super().on_start()
        # get_all() retrieves all record types, record instances and associated metadata
        self.all_records = self.appian.records.get_all()

        # could be either view or list:
        if "endpoint_type" not in CONFIG:	 # could be either view or list:
            logger.error("endpoint_type not found in config.json")
            sys.exit(1)

        self.endpoint_type = CONFIG["endpoint_type"]

        # view - to view records from opaqueId
        # list - to list all the record types from url_stub
        if "view" not in self.endpoint_type and "list" not in self.endpoint_type:
            logger.error(
                "This behavior is not defined for the provided endpoint type. Supported types are : view and list")
            sys.exit(1)

    def on_stop(self):
        logger.info("logging out")
        super().on_stop()

    @task(X)
    def visit_random_record_type_list(self):
        if "list" in self.endpoint_type:
            self.appian.records.visit_record_type()

    @task(X)
    def visit_random_record_and_get_form(self):
        if "view" in self.endpoint_type:
            record_type = random.choice((
                self.appian.records._get_random_record_type(), ""))
            self.appian.records.visit_record_instance_and_get_form(
                record_type=record_type)

    @task(X)
    # this task visits a random record type list and return the SAIL form.
    def visit_random_record_type_list_and_get_form(self):
        if "list" in self.endpoint_type:
            self.appian.records.visit_record_type_and_get_form()

- By calling super().on_start() inside the on_start() function of the locust test you get access to the appian client which allows
  you to call *self.appian.records, self.appian.news, self.appian.actions* etc. These properties allow us to access specific API's
  to for those Appian objects.
- Functions like *XYZ_and_get_form()* access the actual appian object and return its SAIL form as an instance of :ref:`uiform`.
  This class contains methods that helps you interact with the UI.

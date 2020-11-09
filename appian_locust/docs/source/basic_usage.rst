#####################
Locust Guide
#####################

Before running Locust, we'll outline some top-level concepts and what a "locustfile" is.

TaskSet
********************************************

To define a task, annotate a python function with the @task annotation from the Locust library:

.. code-block:: python

    @task
    def get_front_page(self):
        self.client.get('/')


These tasks are composed within a class called a TaskSet, which can be unordered (once again, a TaskSet) or ordered (TaskSequence).

.. code-block:: python

    class LoginTask(AppianTaskSet):
        def on_start(self):
            pass

        @task
        def get_front_page(self):
            self.client.get('/')

        @task
        def get_help_page(self):
            self.client.get('/help')



These together form a locustfile. You can see an example file [here](https://gitlab.com/appian-oss/appian-locust/-/blob/master/example_locustfile.py).

TaskSequence
********************************************
A TaskSequence is similar to a TaskSet, except it allows you to specify the order in which tests should be run.

.. code-block:: python

    class TestTaskSequence(AppianTaskSequence):
        def on_start(self):
            pass

        @seq_task(1)
        def get_front_page(self):
            self.client.get('/')

        @seq_task(2)
        @task(2)
        def get_help_page(self):
            self.client.get('/help')

- `@seq_task` defines the order of the tasks by the value passed in to this decorator. In the example above ``get_front_page`` will execute before ``get_help_page``.
- Along with the ``seq_task`` decorator, one can also define an ``@task`` decorator with a value specifying how many times the given task should execute.
- A Locust-spawned user will repeatedly execute tasks in the order and with the frequency specified by these annotations until the test completes.

HttpUser
********************************************

And lastly, you supply a "Locust", or a representation of a single user that will interact with the system. At runtime you can decide how many users and how fast they should spin up.

.. code-block:: python

    class UserActor(HttpUser):
        wait_time = between(0.5, 0.5)
        tasks = [LoginTask]
        host = "https://my-site.appiancloud.com"

See :ref:`ways_of_running_locust` to see how to run a locust file.

A note on config_utils
********************************************

These two lines look for a ``config.json`` file at the location from which the script is run (not where the locustfile is).

.. code-block:: python

    from appian_locust.loadDriverUtils import utls

    utls.load_config()


This takes the content of the ``config.json`` file and places it into a variable as `utls.c`.
This allows us to access configurations required for logging in inside the class that extends HttpUser:

.. code-block:: python

    config = utls.c
    auth = utls.c['auth']


A minimal `config.json` looks like:

.. code-block:: json

    {
        "cluster_domain": "appiancloud.com",
        "site_name": "site-name",
        "auth": [
            "user.name",
            "password"
        ]
    }

A note on Locust Environments
********************************************

As of Locust 1.0.0, properties of a particular Locust run have been moved into the environment framework.
The best way to get a reference to this environment is to register a listener
for initialization (which includes a reference to it) it and to store this reference:

.. code-block:: python

    from locust import events
    from appian_locust.helper import ENV

    @events.init.add_listener
    def on_locust_init(environment, **kw):
        global ENV
        ENV = environment

    def end_test():
        ENV.runner.greenlet.kill(block=True)

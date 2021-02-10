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



These together form a locustfile. You can see an example file `here <https://gitlab.com/appian-oss/appian-locust/-/blob/master/examples/example_locustfile.py>`_.

SequentialTaskSet
********************************************
A SequentialTaskSet is a TaskSet whose tasks will be executed in the order that they are declared. It is possible to nest SequentialTaskSets within a TaskSet and vice versa.

.. code-block:: python

    class OrderedEndToEndTaskSequence(AppianTaskSequence):
        @task
        def nav_to_random_site(self):
            pass

        @task
        @repeat(5, WAIT_TIME)
        def nav_to_specific_site(self):
            pass

        @task
        @repeat(10, WAIT_TIME)
        def increment_iteration_counter(self):
            if self.iterations >= max_iterations:
                logger.info(f"Stopping the Locust runner")
                ENV.runner.quit()
            else:
                logger.info(f"Incrementing the iteration set counter")
                self.iterations += 1

- A Locust-spawned user will repeatedly execute tasks in the order and with the frequency specified by `@repeat` annotation. In this case test will have to be stopped
  manually by the dev based on some condition. Usually it can be based on a set number of iterations as shown by the example above.
- `WAIT_TIME` passed into @repeat decorator will make sure there is set amount of time between the repetitions of a particular task.
- Taks which do not have the @repeat decorator will only execute one during their turn.

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
        "host_address": "site-name.appiancloud.com",
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
        ENV.runner.quit()

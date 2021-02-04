############################################
Advanced Usage Patterns
############################################


Executing a specific number of tasks
*************************************

One can also write a test that executes a set number of iterations of your TaskSequence Class and all its tasks, instead of executing the test for X number of seconds/mins/hours.
Here's a snippet showing how to run a test for a set number of iterations.

.. code-block:: python

    import json
    import os
    from locust import HttpUser, task, between, events

    from appian_locust import AppianTaskSet

    @events.init.add_listener
    def on_locust_init(environment, **kw):
        global ENV
        ENV = environment


    class OrderedEndToEndTaskSequence(AppianTaskSequence):
        @task
        def nav_to_random_site(self):
            pass

        @task
        def nav_to_specific_site(self):
            pass

        @task
        def increment_iteration_counter(self):
            logger.info(f"Iteration Number: {self.iterations}")
            # Stop the test if 40 iterations of the set have been completed.
            # This would mean approximately 40K requests in total for the test.
            if self.iterations >= CONFIG["num_of_iterations"]:
                logger.info(f"Stopping the Locust runner")
                ENV.runner.quit()
            else:
                logger.info(f"Incrementing the iteration set counter")
                self.iterations += 1

    class UserActor(HttpUser):
        tasks = [GetFrontPageTaskSet]
        config_file = "./example_config.json"
        CONFIG = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as config_file:
                CONFIG = json.load(config_file)
        else:
            raise Exception("No config.json found")
        host = f'https://{CONFIG["host_address"]}'
        auth = CONFIG["auth"]
        wait_time = between(0.500, 0.500)


Note: ``CONFIG["num_of_iterations"]`` is retrieved from the test configuration. This should be provided in the `example_config.json <https://gitlab.com/appian-oss/appian-locust/-/blob/master/example_config.json>`_ file.

The way to achieve specific number of tasks in this test is by having a counter in your task, that you increment once in a specific Locust task and then stop the test when you have reached the desired number of iterations.

Waiting until all users are spawned
*************************************

If you want to wait for your test to spawn all of the Locust users

.. code-block:: python

    from gevent.lock import Semaphore

    all_locusts_spawned = Semaphore()
    all_locusts_spawned.acquire()

    @events.spawning_complete.add_listener
    def on_spawn_complete(**kw):
        print("All news users can start now!")
        all_locusts_spawned.release()

    class WaitingTaskSet(AppianTaskSet):

        def on_start(self):
            """ Executes before any tasks begin."""
            super().on_start()
            all_locusts_spawned.wait()

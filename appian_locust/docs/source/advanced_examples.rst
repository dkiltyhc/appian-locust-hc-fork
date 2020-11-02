############################################
Advanced Usage Patterns
############################################


Executing a specific number of tasks
*************************************

One can also write a test that executes a set number of iterations of your TaskSequence Class and all its tasks, instead of executing the test for X number of seconds/mins/hours.
Here's a snippet showing how to run a test for a set number of iterations.

.. code-block:: python

    class OrderedEndToEndTaskSequence(AppianTaskSequence):
        @task
        def nav_to_random_site(self):
            pass

        @task
        def nav_to_specific_site(self):
            pass

        @task
        def increment_iteration_counter(self):
            if self.iterations >= max_iterations:
                logger.info(f"Stopping the Locust runner")
                ENV.runner.greenlet.kill(block=True)
            else:
                logger.info(f"Incrementing the iteration set counter")
                self.iterations += 1


The way to achieve this is by having a counter in your task, that you increment once in a specific Locust task and then stop the test when you have reached the desired number of iterations.

Waiting until all users are spawned
*************************************

If you want to wait for your test to spawn all of the Locust users

.. code-block:: python

    from gevent.lock import Semaphore

    all_locusts_spawned = Semaphore()
    all_locusts_spawned.acquire()

    @events.hatch_complete.add_listener
    def on_hatch_complete(**kw):
        print("All news users can start now!")
        all_locusts_spawned.release()

    class WaitingTaskSet(AppianTaskSet):

        def on_start(self):
            """ Executes before any tasks begin."""
            super().on_start()
            all_locusts_spawned.wait()

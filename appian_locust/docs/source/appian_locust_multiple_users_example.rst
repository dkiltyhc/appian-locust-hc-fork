############################
Locust Test Example: Multiple Users
############################

An example of a Locust Test showing interaction with the frontend and admin pages - `example_multi_user_locustfile.py <https://gitlab.com/appian-oss/appian-locust/-/blob/master/examples/example_multi_user_locustfile.py>`_.

This test has 2 locust TaskSets defined and 2 HttpUsers defined that simulate different login information.

TaskSets
########
- The ``GetFrontPageTaskSet`` simply navigates to a basic user landing page
- The ``GetAdminPageTaskSet`` navigates to the admin console

HttpUsers
#########
- The ``FrontendUserActor`` uses the login credentials for the regular frontend user
- The ``AdminUserActor`` uses the login credentials for the admin user

Running
#########

When running this locustfile, it is important to note that the users specified when running are spread evenly across the HttpUsers.
If you only specify one user to run when running locust, it will only choose one user actor to start:

.. code-block:: bash

    locust -f examples/example_multi_user_locustfile.py --headless -r 10 -t 3600 --users 1
    ...
    All users hatched: FrontendUserActor: 1, AdminUserActor: 0 (0 already running)


Make sure to run the locustfile with at least as many users as required by how you have the `weights <https://docs.locust.io/en/stable/writing-a-locustfile.html#weight-attribute>`_ configured for each HttpUser.

For the included sample, the weights are 3 and 1 respectively, meaning you'll have to spawn 4 users to get the ``AdminUserActor`` to start up


.. code-block:: bash

    locust -f examples/example_multi_user_locustfile.py  --headless -r 10 -t 3600 --users 4
    ...
    All users hatched: FrontendUserActor: 3, AdminUserActor: 1 (0 already running)

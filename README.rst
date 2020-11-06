.. what_is_appian_locust-inclusion-begin-do-not-remove
#######################################
What is Appian Locust?
#######################################

This is a set of helper libraries built on top of Locust.
These are tools for interacting with Appian for load testing purposes, as well as a few helpers to store and use configurations when testing.

Here are example capabilities

- Form interactions
- Logging in and logging out
- Finding components in a SAIL interface
- Navigating to records/reports/sites

.. what_is_appian_locust-inclusion-end-do-not-remove


For full documentation, visit the `docs page <https://appian-locust.readthedocs.io/en/latest/>`__

.. quick_start-inclusion-begin-do-not-remove
********************
Quick Start Guide
********************

This is a quick guide to getting up and running with the appian-locust library. You will need Python 3.7+ installed on your machine before proceeding.

Setup
------------

1. Install appian-locust using `pip`, for more comprehensive projects we recommend using `pipenv`.

  .. code-block:: bash

      pip install appian-locust

2. Configure your test to point at the Appian instance you will be using. In `example_config.json`:

  - Set `site_name` and `cluster_domain` to the address of your Appian instance.
  - In `auth`, specify the username and password of the user account to use.

  .. code-block:: json

      {
          "cluster_domain": "appiancloud.com",
          "site_name": "site-name",
          "auth": [
              "user.name",
              "password"
          ]
      }

3. Run the sample test `example_locustfile.py`.

  .. code-block:: bash

      locust -f example_locustfile.py -u 1 -t 60 --headless

If everything is set up correctly, you should start to see output from the load test reporting results. This should run for 60 seconds and end with a summary report of the results.

* For more examples of different site interactions, see the `example_*.py` files included in this repository.
* For more in-depth information about the test library, see the rest of this documentation.

Troubleshooting:
----------------
* **"Failed to establish a new connection: [Errno 8] nodename nor servname provided, or not known"**

  * check that `cluster_domain` and `site_name` are specified correctly in `example_config.json`.

* **"Login unsuccessful, no multipart cookie found...make sure credentials are correct"**

  * check that `auth` specifies a valid username and password combination for the site you're testing on in `example_config.json`.

.. quick_start-inclusion-end-do-not-remove
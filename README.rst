.. what_is_appian_locust-inclusion-begin-do-not-remove

#######################################
What is Appian Locust?
#######################################

Appian Locust is a wrapper library around `Locust <https://locust.io>`__ for load testing Appian.
This library is intended to be used as an alternative to tools such as Jmeter and Load Runner.

Appian Locust capabilities

- Logging in and logging out
- Form interactions (filling/submitting)
- Finding and interacting with basic components on a SAIL interface
- Navigating to records/reports/sites

.. what_is_appian_locust-inclusion-end-do-not-remove


For full documentation, visit the `docs page <https://appian-locust.readthedocs.io/en/latest/>`__

.. disclaimer-inclusion-begin-do-not-remove

**Disclaimer:**
This library is continuously evolving.
Currently the main focus is supporting essential use-cases.
We are happy to accept contributions to further extend functionality, address bug fixes and improve usability.
Please see the `Contributing <contributing.html>`__ section and feel free to reach out.

.. disclaimer-inclusion-end-do-not-remove

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

  - Set `host_address` to the address of your Appian instance.
  - In `auth`, specify the username and password of the user account to use.

  .. code-block:: json

      {
          "host_address": "site-name.appiancloud.com",
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

Troubleshooting
----------------
* **"Failed to establish a new connection: [Errno 8] nodename nor servname provided, or not known"**

  * check that `host_address` is specified correctly in `example_config.json`.

* **"Login unsuccessful, no multipart cookie found...make sure credentials are correct"**

  * check that `auth` specifies a valid username and password combination for the site you're testing on in `example_config.json`.

.. quick_start-inclusion-end-do-not-remove

.. contrib-inclusion-begin-do-not-remove

********************
Contributing
********************

* Read and agree to our `Contributing Policy <https://gitlab.com/appian-oss/appian-locust/-/blob/master/CONTRIBUTING>`__
* Fork the `appian-locust <https://gitlab.com/appian-oss/appian-locust>`__ repository
* Make any desired changes to python files, etc.
* Commit changes and push to your fork
* Make a merge request to the upstream fork

To test changes
-----------------
In any test-implementation repo where you use appian-locust, change the following (assuming you're using a ``Pipfile``)

.. code-block:: python

    appian-locust = {path="../appian-locust", editable=true}

**NOTE** The path above assumes appian-locust is checked out locally, hence we can use a relative directory path.

And run ``pipenv install --skip-lock`` to allow you to use a local version of appian-locust
without recreating the lock file. However, remember to use a lock file in your test-implementation repo.

Now you can test your changes as you normally would.

.. contrib-inclusion-end-do-not-remove


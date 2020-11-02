#################
Quick Start Guide
#################

This is a quick guide to getting up and running with the appian-locust library. You will need Python 3.7.4+ installed on your machine before proceeding.

1. Install pipenv to allow for creating a virtual environment for your load test to run in:

.. code-block:: bash

    pip3 install pipenv

2. Install the appian-locust testing library:

.. code-block:: bash

    pipenv install appian-locust

3. Configure your load test to point at the Appian instance you will be using. In `example_config.json`:
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

4. Run the sample test `example_locustfile.py`.

.. code-block:: bash

    pipenv run locust -f example_locustfile.py -u 1 -t 60 --headless

* If you see the error message "Failed to establish a new connection: [Errno 8] nodename nor servname provided, or not known", check that `cluster_domain` and `site_name` are specified correctly in `example_config.json`.
* If you see the error message "Login unsuccessful, no multipart cookie found...make sure credentials are correct", check that `auth` specifies a valid username and password combination for the site you're testing on in `example_config.json`.

If everything is set up correctly, you should start to see output from the load test reporting results. This should run for 60 seconds and end with a summary report of the results.

* For more examples of different site interactions, see the `example_*.py` files included in this repository.
* For more in-depth information about the test library, see the rest of this documentation.

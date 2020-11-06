####################
Contributing
####################

* Read and agree to our `Contributing Policy <https://gitlab.com/appian-oss/appian-locust/-/blob/master/CONTRIBUTING>`__
* Fork the `appian-locust <https://gitlab.com/appian-oss/appian-locust>`__ repository
* Make any desired changes to python files, etc.
* Commit changes and push to your fork
* Make a merge request to the prod fork

To test changes
****************
In any downstream repo where you use appian-locust, change the following (assuming you're using a Pipfile)

.. code-block:: python

    appian-locust = {path="../appian-locust", editable=true}


And run ``pipenv install --skip-lock`` to allow you to use a local version of appian-locust without recreating the loc file

**NOTE** The path given above assumes appian-locust is checked out in a relative directory

You can run your changes as you would following the :ref:`ways_of_running_locust` section

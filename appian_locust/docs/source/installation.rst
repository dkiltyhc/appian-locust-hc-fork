*********************************************************************
Installation
*********************************************************************

Install from pypi
-----------------

The performance library is known by the python package name "appian-locust".

Simple ``pip install``:

.. code-block:: bash

    pip install appian-locust


It's recommended to use pipenv to manage dependencies but any dependency management tool
(poetry, pip, etc.) should work.

If using ``pipenv``, simply start from the following ``Pipfile``:

.. code-block:: toml

    [packages]
    appian-locust = {version = "*"}

    [requires]
    python_version = "3.7"

    [pipenv]
    allow_prereleases = true

Installing from source
----------------------

It’s highly recommended that you use a virtual environment when installing python artifacts.
You can follow the instructions `here <https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/>`__ to install virtualenv and pip.

It's recommended to use a dependency management tool as mentioned above, but the below example installs the library globally.

You’ll need to clone the repository first

.. code-block:: bash

    git clone -o prod git@gitlab.com:appian-oss/appian-locust.git


Once that is done, you can simply use

.. code-block:: bash

    pip install -e appian-locust


to install the library globally.

If you’re using a virtualenv or a dependency management tool (e.g. ``pipenv``), you can do the same type of install, but you will want to be in the context of the virtualenv (i.e. source the virtualenv), and you’ll need to pass the path to the repository you cloned.

If you have issues installing, make sure you have the proper prerequisites installed for Locust and its dependencies.
If you're having trouble on Windows, check `here <https://github.com/locustio/locust/issues/1208#issuecomment-569693439>`__

.. include:: ../../../README.rst
  :start-after: what_is_appian_locust-inclusion-begin-do-not-remove
  :end-before: what_is_appian_locust-inclusion-end-do-not-remove

What is Locust?
_________________________________

It’s an open source python library for doing load testing (think `JMeter <https://jmeter.apache.org/>`_, but in Python).
It is by default HTTP-driven, but can be made to work with other types of interactions.
Visit `Locust <https://docs.locust.io/en/stable/>`__ for more information.

Locust has the benefit of relying purely on API requests, which makes it lower overhead than frameworks building
on Selenium or browser automation libraries. We have also found python to be common denominator across software and quality engineers,
making it a convenient language for extending the framework and defining tests.
Locust's model of ``TaskSets`` and ``TaskSequences``, it is easy to compose user operations while maintaining the details in code,
Appian-Locust builds on this concepts by defining :class:`.AppianTaskSet` and :class:`.AppianTaskSequence`, which layer on Appian-specific
functionality such as login and session management.
For more detail information, see the `Appian Locust Guide <basic_usage.html#locust-guide>`__.


SAIL Navigation
_________________________________


Appian interfaces are built with `SAIL <https://docs.appian.com/suite/help/20.3/SAIL_Design.html>`__.
It's a RESTful contract that controls state between the browser/mobile clients and the server.

All SAIL-based interactions require updating a server-side context (or in a stateless mode, passing that context back and forth).
These updates are expressed as JSON requests sent back and forth, which are sent as "SaveRequests", usually to the same endpoint from which the original SAIL form was served. Each SaveRequest, if successful, will return an updated component, or a completely new form if a modal is opened or a button is clicked on a wizard.

Most of the interactions we deal with in this library are SAIL-related.
The ``uiform.py`` file or ``SailUiForm`` class are entirely built on sending and receiving SAIL requests, as are a lot of the other interactions we perform.
Sometimes the best way to verify that we're doing the right thing is by opening the browser network tab and looking at the XHR requests generated as one interacts with Appian.

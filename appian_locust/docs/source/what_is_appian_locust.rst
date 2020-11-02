#######################################
What is the Appian Performance Library?
#######################################

This is a set of helper libraries built on top of Locust.
These are tools for interacting with Appian for load testing purposes, as well as a few helpers to store and use configurations when testing.

Here are example capabilities

- Form interactions
- Logging in and logging out
- Finding components in a SAIL interface
- Navigating to records/reports/sites

What is Locust?
_______________________________________

It’s an open source python library for doing load testing (think `JMeter <https://jmeter.apache.org/>`_, but in Python).
It is by default HTTP-driven, but can be made to work with other types of interactions.
Visit `Locust <https://docs.locust.io/en/stable/>`__ for more information.


SAIL Navigation
_________________________________


Appian interfaces are built with `SAIL <https://docs.appian.com/suite/help/20.3/SAIL_Design.html>`__.
It's a RESTful contract that controls state between the browser/mobile clients and the server.

All SAIL-based interactions require updating a server-side context (or in a stateless mode, passing that context back and forth).
These updates are expressed as JSON requests sent back and forth, which are sent as "SaveRequests", usually to the same endpoint from which the original SAIL form was served. Each SaveRequest, if successful, will return an updated component, or a completely new form if a modal is opened or a button is clicked on a wizard.

Most of the interactions we deal with in this library are SAIL-related.
The ``uiform.py`` file or ``SailUiForm`` class are entirely built on sending and receiving SAIL requests, as are a lot of the other interactions we perform.
Sometimes the best way to verify that we're doing the right thing is by opening the browser network tab and looking at the XHR requests generated as one interacts with Appian.

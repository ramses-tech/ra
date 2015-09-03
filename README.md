# ra

``ra`` is a test suite generator and helper library for testing APIs described
by [RAML](http://raml.org/) documents.

Out of the box, `ra` provides a basic, automated test suite to test the routes
declared in the RAML document. It provides test helpers for augmenting these
with custom tests to test application-specific logic, side effects, etc.

## Name

Ra was the god of the sun, the most important god in ancient Egypt.

`ra` is primarily designed to provide testing support for
[ramses](http://github.com/brandicted/ramses) and
[nefertari](http://github.com/brandicted/nefertari) applications, but can
be used with any WSGI-conformant, RAML-described API.

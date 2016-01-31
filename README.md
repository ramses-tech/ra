# `Ra`
[![Build Status](https://travis-ci.org/ramses-tech/ra.svg?branch=master)](https://travis-ci.org/ramses-tech/ra)
[![Documentation](https://readthedocs.org/projects/ra/badge/?version=stable)](http://ra.readthedocs.org)

Ra is a test suite generator and helper library for testing APIs described
in [RAML](http://raml.org/).

Out of the box, Ra provides a basic, automated test suite to test the routes
declared in the RAML document. It provides test helpers for augmenting these
with custom tests to test application-specific logic, side effects, etc.

Ra is primarily designed to provide testing support for
[ramses](http://github.com/ramses-tech/ramses) and
[nefertari](http://github.com/ramses-tech/nefertari) applications, but can
be used with any WSGI-conformant, RAML-described API.

It currently depends on pytest but may be adapted for other test frameworks
in the future. It works best using WebTest but doesn't require it.

## Name

Ra was the god of the sun, the most important god in ancient Egypt.


## Try it (dev)

Run the test suite:

```bash
    $ pip install -r requirements.txt
    $ py.test
```

Check out the example:

```bash
    $ cd examples/ramses-test
    $ pip install -r requirements.txt
    $ py.test
```

The example RAML at `examples/ramses-test/api.raml` and the test file
`examples/ramses-test/tests/test_api.py` should be helpful to reference.

See the docs in `docs/`, and the `api.raml` and `tests/test_api.py` in
`tests/apps/ramses_test`


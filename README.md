# OSF

The code for [https://osf.io](https://osf.io).

- `master` ![Build Status](https://github.com/CenterForOpenScience/osf.io/workflows/osf.io/badge.svg?branch=master)
- `develop` ![Build Status](https://github.com/CenterForOpenScience/osf.io/workflows/osf.io/badge.svg?branch=develop)
- Versioning Scheme:  [![CalVer Scheme](https://img.shields.io/badge/calver-YY.MINOR.MICRO-22bfda.svg)](http://calver.org)
- Issues: https://github.com/CenterForOpenScience/osf.io/issues?state=open
- COS Development Docs: http://cosdev.readthedocs.org/

Selenium end-to-end automated tests
- ![production_smoke_tests](https://github.com/cos-qa/osf-selenium-tests/actions/workflows/production_smoke_tests.yml/badge.svg)
- ![nightly_core_functionality_tests](https://github.com/cos-qa/osf-selenium-tests/actions/workflows/nightly_core_functionality_tests.yml/badge.svg)
- ![weekly_regression_tests](https://github.com/cos-qa/osf-selenium-tests/actions/workflows/weekly_regression_tests.yml/badge.svg)

## Running the OSF For Development

To run the OSF for local development, see [README-docker-compose.md](https://github.com/CenterForOpenScience/osf.io/blob/develop/README-docker-compose.md).

Optional, but recommended: To set up pre-commit hooks (will run
formatters and linters on staged files):

```
pip install pre-commit

pre-commit install --allow-missing-config
```

## More Resources

The [COS Development Docs](http://cosdev.readthedocs.org/) provide detailed information about all aspects of OSF development.
This includes style guides, process docs, troubleshooting, and more.

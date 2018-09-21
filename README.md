# OSF

The code for [https://osf.io](https://osf.io).

- `master` Build Status: [![Build Status](https://travis-ci.org/CenterForOpenScience/osf.io.svg?branch=master)](https://travis-ci.org/CenterForOpenScience/osf.io)
- `develop` Build Status: [![Build Status](https://travis-ci.org/CenterForOpenScience/osf.io.svg?branch=develop)](https://travis-ci.org/CenterForOpenScience/osf.io)
- Versioning Scheme:  [![CalVer Scheme](https://img.shields.io/badge/calver-YY.MINOR.MICRO-22bfda.svg)](http://calver.org)
- Issues: https://github.com/CenterForOpenScience/osf.io/issues?state=open
- COS Development Docs: http://cosdev.readthedocs.org/


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

[This repository has moved; click here.](http://github.com/CenterForOpenScience/openscienceframework/)
===========================

Quickstart
==========

These instructions should work on Mac OSX >= 10.7

- Create your virtualenv.
- Install MongoDB. On MacOSX with [homebrew](http://brew.sh/) (click link for homebrew installation instructions), run:

```bash
$ brew update 
$ brew install mongodb
```

- Install libxml2 and libxslt (required for installing lxml).

```bash
$ brew install libxml2
$ brew install libxslt
```

- Install requirements.

```bash
$ pip install -r requirements.txt
```

- Run your mongodb process.

```bash
$ make mongodb
```

- Run your local development server.

```bash
$ make server
```

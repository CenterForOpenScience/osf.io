[This repository has moved; click here.](http://github.com/CenterForOpenScience/openscienceframework/)
===========================

## Quickstart

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
$ pip install -r dev-requirements.txt
```

- Create your local settings file.

```bash
$ cp website/settings/local-dist.py website/settings/local.py
```

`local.py` will override settings in `base.py`. It will not be added to source control, so change it as you wish.

## Starting Up

- Run your mongodb process.

```bash
$ invoke mongo
```

- Run your local development server.

```bash
$ invoke server
```

## Running Tests

To run all tests:

```bash
$ invoke test
```

To run a certain test method

```bash
$ nosetests tests/test_module.py:TestClass.test_method
```

### Testing Email


First, set `MAIL_SERVER` to `localhost:1025` in you `local.py` file.

website/settings/local.py

```python
...
MAIL_SERVER = "localhost:1025"
...
```

Then fire up a pseudo-mailserver with:

```bash
$ invoke mailserver -p 1025
```

## Using Celery

### Installing Celery + RabbitMQ

- Install RabbitMQ. On MacOSX with homebrew,

```bash
$ brew update
$ brew install rabbitmq
```
The scripts are installed to `/usr/local/sbin`, so you may need to add `PATH=$PATH:/usr/local/sbin` to your `.bash_profile`.

For instructions for other OS's, see [the official docs](http://www.rabbitmq.com/download.html).

Then start the RabbitMQ server with

```bash
$ invoke rabbitmq
```

If you want the rabbitmq server to start every time you start your computer (MacOSX), run

```bash
$ ln -sfv /usr/local/opt/rabbitmq/*.plist ~/Library/LaunchAgents
$ launchctl load ~/Library/LaunchAgents/homebrew.mxcl.rabbitmq.plist
```

### Starting A Celery Worker

```bash
invoke celery_worker
```

## Using Solr

### Installing Solr

- Make sure [Java is installed](https://www.java.com/en/download/help/index_installing.xml)
- Install solr. On MacOSX with Homebrew:

```bash
$ brew update
$ brew install solr
```

- Migrate the models.

```bash
$ invoke solr_migrate
```

### Starting A Local Solr Server

```bash
$ invoke solr
```

This will start a Solr server on port 8983.







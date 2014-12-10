# OSF


- `master` Build Status: [![Build Status](https://travis-ci.org/CenterForOpenScience/osf.io.svg?branch=master)](https://travis-ci.org/CenterForOpenScience/osf.io)
- `develop` Build Status: [![Build Status](https://travis-ci.org/CenterForOpenScience/osf.io.svg?branch=master)](https://travis-ci.org/CenterForOpenScience/osf.io)
- Public Repo: https://github.com/CenterForOpenScience/osf.io/
- Issues: https://github.com/CenterForOpenScience/osf.io/issues?state=open
- Huboard: https://huboard.com/CenterForOpenScience/osf.io#/
- Docs: http://cosdev.rtfd.org/

> ## Help

Solutions to many common issues may be found at the [OSF Developer Docs](http://cosdev.rtfd.org/).

## Quickstart

These instructions should work on Mac OSX >= 10.7

- Create your virtualenv.

- Copy `website/settings/local-dist.py` to `website/settings/local.py.`  NOTE: This is your local settings file, which overrides the settings in `website/settings/defaults.py`. It will not be added to source control, so change it as you wish.

```bash
$ cp website/settings/local-dist.py website/settings/local.py
```

- You will need to:
    - Create local.py files for addons that need them.
    - Install TokuMX.
    - Install libxml2 and libxslt (required for installing lxml).
    - Install elasticsearch.
    - Install GPG.
    - Install requirements.
    - Create a GPG key.
    - Install npm
    - Install bower
    - Use bower to install Javascript components

- To do so, on MacOSX with [homebrew](http://brew.sh/) (click link for homebrew installation instructions), run:

```bash
$ pip install invoke
$ invoke setup
```


- Optionally, you may install the requirements for the Modular File Renderer:

```bash
$ invoke mfr_requirements
```

and for addons:

```bash
$ invoke addon_requirements
```

- On Linux systems, you may have to install python-pip, TokuMX, libxml2, libxslt, elasticsearch, and GPG manually before running the above commands.

- If invoke setup hangs when 'Generating GnuPG key' (especially under linux), you may need to install some additonal software to make this work. For apt-getters this looks like:

```bash
sudo apt-get install rng-tools
```

next edit /etc/default/rng-tools and set:

```
HRNGDEVICE=/dev/urandom
```

last start the rng-tools daemon with:

```
sudo /etc/init.d/rng-tools start
```

__source: http://www.howtoforge.com/helping-the-random-number-generator-to-gain-enough-entropy-with-rng-tools-debian-lenny __

## Starting Up

- Run your mongodb process.

```bash
$ invoke mongo
```

- Run your local development server.

```bash
$ invoke server
```

## Running the shell

To open the interactive Python shell, run:

```bash
$ invoke shell
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

### Testing Addons

Addons tests are not run by default. To execute addons tests, run

```bash
$ invoke test_addons
```

### Testing Email


First, set `MAIL_SERVER` to `localhost:1025` in you `local.py` file.

website/settings/local.py

```python
...
MAIL_SERVER = "localhost:1025"
...
```

Sent emails will show up in your server logs.

*Optional*: fire up a pseudo-mailserver with:

```bash
$ invoke mailserver -p 1025
```

## Using TokUMX

TokuMX is an open-source fork of MongoDB that provides support for transactions in single-sharded environments.
TokuMX supports all MongoDB features as of version 2.4 and adds `beginTransaction`, `rollbackTransaction`, and
`commitTransaction` commands.

If you don't want to install TokuMX, set `USE_TOKU_MX` to `False` in `website/settings/local.py`.

### Installing with Mac OS

```bash
$ brew tap tokutek/tokumx
$ brew install tokumx-bin
```

### Installing on Ubuntu

```bash
$ apt-key adv --keyserver keyserver.ubuntu.com --recv-key 505A7412
$ echo "deb [arch=amd64] http://s3.amazonaws.com/tokumx-debs $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/tokumx.list
$ apt-get update
$ apt-get install tokumx
```

### Migrating from MongoDB

TokuMX and MongoDB use different binary formats. To migrate data from MongoDB to TokuMX:
* Back up the MongoDB data
    * `invoke mongodump --path dump`
* Shut down the MongoDB server
* Uninstall MongoDB
* Install TokuMX (see instructions above)
* Restore the data to TokuMX
    * `invoke mongorestore --path dump/osf20130903 --drop`
* Verify that the migrated data are available in TokuMX

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

## Using Search

### Elasticsearch

- Install Elasticsearch

#### Mac OSX

```bash
$ brew install elasticsearch
```
_note: Oracle JDK 7 must be installed for elasticsearch to run_

#### Ubuntu

```bash
$ wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.2.1.deb
$ sudo dpkg -i elasticsearch-1.2.1.deb
```

#### Using Elasticsearch
- In your `website/settings/local.py` file, set `SEARCH_ENGINE` to 'elastic'.

```python
SEARCH_ENGINE = 'elastic'
```
- Start the Elasticsearch server and migrate the models.

```bash
$ invoke elasticsearch
$ invoke migrate_search
```
#### Starting a local Elasticsearch server

```bash
$ invoke elasticsearch
```

## NPM

The Node Package Manager (NPM) is required for installing a number of node-based packages.

```bash
# For MacOSX
$ brew update && brew install node
```

Installing Node on Ubuntu is slightly more complicated. Node is installed as `nodejs`, but Bower expects
the binary to be called `node`. Symlink `nodejs` to `node` to fix, then verify that `node` is properly aliased:

```bash
# For Ubuntu
$ sudo apt-get install nodejs
$ sudo ln -s /usr/bin/nodejs /usr/bin/node
$ node --version      # v0.10.25
```


## Install NPM requirements

To install necessary NPM requiremnts, run:

```bash
$ npm install
```

In the OSF root directory.

## Using Bower to install front-end dependencies

We use [bower](http://bower.io/) to automatically download and manage dependencies for front-end libraries. This should
be installed with `invoke setup` (above)

To get the bower CLI, you must have `npm` installed.

```bash
$ npm install -g bower
```

### To update existing front-end dependencies

This will be the most common command you will use with `bower`. It will update all your front-end dependencies to the version required by the OSF. Think of it as the `pip install -r requirements.txt` for front-end assets.

```bash
$ bower install
```

### To add a new front-end library

Use this command when adding a new front-end dependency

```bash
$ bower install zeroclipboard --save
```

The `--save` option automatically adds an entry to the `bower.json` after downloading the library.

This will save the library in `website/static/vendor/bower_components/`, where it can be imported like any other module.

## Using webpack for asset bundling and minification

We use [webpack](https://webpack.github.io/docs/) to bundle and minify our static assets.

To get the webpack CLI, you must have `npm` installed.

```bash
$ npm install -g webpack
```

### To build assets with webpack

```bash
# Make sure dependencies are up to date
$ bower install && npm install
# Run webpack in watch mode
$ inv pack -w
```

The above commands can be run in one step with:

```bash
$ inv assets -w
```

## Setting up addons

To install the python libraries needed to support the enabled addons, run:

```bash
$ invoke addon_requirements
```

### Getting application credentials

Many addons require application credentials (typically an app key and secret) to be able to authenticate through the OSF. These credentials go in each addon's `local.py` settings file (e.g. `website/addons/dropbox/settings/local.py`).

For local development, the COS provides test app credentials for a number of services. A listing of these can be found here: https://osf.io/m2hig/wiki/home/ .

## Summary

If you have all the above services installed, you can start *everything* up with this sequence

```bash
invoke mongo -d  # Runs mongod as a daemon
invoke mailserver
invoke rabbitmq
invoke celery_worker
invoke elasticsearch
bower install
invoke pack -w
invoke server
```


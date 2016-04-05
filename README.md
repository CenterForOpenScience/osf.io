# OSF

- `master` Build Status: [![Build Status](https://travis-ci.org/CenterForOpenScience/osf.io.svg?branch=master)](https://travis-ci.org/CenterForOpenScience/osf.io)
- `develop` Build Status: [![Build Status](https://travis-ci.org/CenterForOpenScience/osf.io.svg?branch=develop)](https://travis-ci.org/CenterForOpenScience/osf.io)
- Public Repo: https://github.com/CenterForOpenScience/osf.io/
- Issues: https://github.com/CenterForOpenScience/osf.io/issues?state=open
- COS Development Docs: http://cosdev.readthedocs.org/

## Table of contents
- [Help](#help)
- [Running the OSF](#running-the-osf)
- [Running the API Server] (#running-the-api-server)
- [Installation](#installation)
- [Common Development Tasks](#common-development-tasks)



## Help
The [COS Development Docs](http://cosdev.readthedocs.org/) provide detailed information about all aspects of OSF development.
This includes [detailed installation instructions](http://cosdev.readthedocs.org/en/latest/osf/setup.html),
a list of [common setup errors](http://cosdev.readthedocs.org/en/latest/osf/setup.html#common-error-messages), and
[other troubleshooting](http://cosdev.readthedocs.org/en/latest/osf/common_problems.html).

The OSF `invoke` script provides several useful commands. For more information, run:

`invoke --list`

## Running the OSF

If you have already installed all of the required services and Python packages, and activated your virtual environment,
then you can start a working local test server with the following sequence:

```bash
invoke mongo -d  # Runs mongod as a daemon
invoke mailserver
invoke rabbitmq
invoke celery_worker
invoke elasticsearch
invoke assets -dw
invoke server
```

Note that some or all of these commands will run attached to a console, and therefore the commands may need to be
run in separate terminals. Be sure to activate your virtual environment each time a new terminal is opened.
It is normal for the command to keep running!

Once started, you will be able to view the OSF in a web browser- by default, at http://127.0.0.1:5000/

In order to log in on your local server, you will also need to run the authentication server.

- For daily use, run fakeCAS. See [CenterForOpenScience/fakeCAS](https://github.com/CenterForOpenScience/fakeCAS) for information on how to set up this service.
- For developing authentication-related features, run CAS. See [CenterForOpenScience/docker-library/cas](https://github.com/CenterForOpenScience/docker-library/tree/master/cas) for information on how to set up this service.

### Running the API Server

If you have already installed all of the required services and Python packages, and activated your virtual environment,
then you can start a working local API server with the sequence delineated under [running the OSF] (#running-the-osf) and:

```bash
invoke apiserver
```

Browse to `localhost:8000/v2/` in your browser to go to the root of the browsable API. If the page looks strange, 
run `python manage.py collectstatic` to ensure that CSS files are deposited in the correct location.


### Livereload support

You can run the OSF server in livereload mode with:

```bash
$ invoke server --live
```

This will make your browser automatically refresh whenever a code change is made.

### Optional extras

Some functionality depends on additional services that will not be started using the sequence above.
For many development tasks, it is sufficient to run the OSF without these services, except as noted below.
Some additional installation will be needed to use these features (where noted), in which case updates will also need 
to be installed separately.

#### Authentication
An authentication server (either CAS or FakeCAS) must be available in order to log in to the OSF while running locally. 
This must be installed separately from the OSF. See [running the OSF](#running-the-osf) for details.

#### Waterbutler

Waterbutler is used for file storage features. Upload and download features will be disabled if Waterbutler is not
installed. Consult the Waterbutler
[repository](https://github.com/CenterForOpenScience/waterbutler) and
[documentation](https://waterbutler.readthedocs.org/en/latest/) for information on how to set up and run this service.

#### Modular File Renderer

The Modular File Renderer (MFR) is used to render uploaded files to HTML via an iFrame so that they can be 
viewed directly on the OSF. Files will not be rendered if the MFR is not running. Consult the 
MFR [repository] (https://github.com/CenterForOpenScience/modular-file-renderer) for information on how to install 
and run the MFR.

#### Sharejs

ShareJS is used for collaborative editing features, such as the OSF wiki. It will be installed by the OSF installer 
script, but must be run separately. To run a local ShareJS server:

```bash
$ invoke sharejs
```

#### Downloading citation styles

To download citation styles, run:

```bash
$ invoke update_citation_styles
```

## Installation

These instructions assume a working knowledge of package managers and the command line.
For a detailed step-by-step walkthrough suitable for new programmers, consult the
[COS Development Docs](http://cosdev.readthedocs.org/en/latest/osf/setup.html). See [optional extras](#optional-extras) 
for information about services not included in the automated install process below.

### Pre-requisites

Before attempting to run OSF setup commands, be sure that your system meets the following minimum requirements.

#### Mac OS

The following packages must be installed before running the automatic setup script:

- [XCode](https://developer.apple.com/xcode/downloads/) command line tools (`xcode-select --install`)
- [Homebrew](http://brew.sh/) package manager (run `brew update` and `brew upgrade --all` before OSF install)
- Java (if not installed yet, run `brew install Caskroom/cask/java`)
- Python 2.7
    - pip
    - virtualenv (`pip install virtualenv`)

##### El Capitan and newer
If you are using Mac OS X >= 10.11 (El Capitan), you will also 
[need](http://lists.apple.com/archives/macnetworkprog/2015/Jun/msg00025.html) to install OpenSSL headers 
and [set](http://cryptography.readthedocs.org/en/latest/installation/#building-cryptography-on-os-x) some configuration:
```bash 
brew install openssl
env LDFLAGS="-L$(brew --prefix openssl)/lib" CFLAGS="-I$(brew --prefix openssl)/include" pip install cryptography
```

### Quickstart

#### Mac OS X
These instructions should work on Mac OSX >= 10.7

- Clone the OSF repository to your computer. Change to that folder before running the commands below.
- Create and activate your virtualenv.
```bash
virtualenv env
source env/bin/activate
```

- Copy `cp website/settings/local-dist.py` to `website/settings/local.py`.  NOTE: This is your local settings file,
which overrides the settings in `website/settings/defaults.py`. It will not be added to source control, so change
it as you wish.
- Copy `cp api/base/settings/local-dist.py` to `api/base/settings/local.py`.  NOTE: This is your local settings file,
which overrides the settings in `website/settings/defaults.py`. It will not be added to source control, so change
it as you wish.

```bash
$ cp website/settings/local-dist.py website/settings/local.py
$ cp api/base/settings/local-dist.py api/base/settings/local.py
```

- On MacOSX with [homebrew](http://brew.sh/), there is a script that should automate much of the install process:

```bash
$ pip install invoke
$ invoke setup
```

To verify that your installation works, follow the instructions to [start the OSF](#running-the-osf) and
[run unit tests](#running-tests).

##### Additional configuration for Mac OS X

After running the automatic installer, you may find that some actions- such as running unit tests- fail due to an error
with Mongo/ TokuMX. This can be resolved by increasing the system limits on number of open files and processes.

Add the following lines to `/etc/launchctl.conf` and/or `/etc/launchd.conf` (creating the files if necessary):
```
limit maxfiles 16384 16384
limit maxproc 2048 2048
```

Then create or edit either `~/.bash_profile` or `/etc/profile` to include the following:

`ulimit -n 2048`

Then reboot.

#### Additional things to install

The automated installer does not install CAS, Waterbutler, or MFR, which may be needed to run some OSF features locally.
Consult the [optional extras](#optional-extras) section for more details.

### Manual installation
[At present](CONTRIBUTING.md), there is no complete automated install process for other platforms.
Although the process above should perform most setup steps on Mac OS, users of other platforms will need to perform the
steps below manually in a manner appropriate to their system. Some steps of the installer script can be re-used,
in which case the appropriate commands are noted below.

On Mac OS, we recommend using Homebrew to install external dependencies.

- Create local.py files for addons that need them (`invoke copy_settings --addons`)
- Install TokuMX
- Install libxml2 and libxslt (required for installing python lxml)
- Install Java (if not already installed)
- Install elasticsearch
- Install GPG
- Install python requirements (`invoke requirements --dev --addons`)
- Create a GPG key (`invoke encryption`)
- Install npm
- Install node and bower packages
- Build assets (`invoke assets --dev`)

- If invoke setup hangs when 'Generating GnuPG key' (especially under linux), you may need to install some
additional software to make this work. For apt-getters this looks like:

```bash
sudo apt-get install rng-tools
```

Followed by editing `/etc/default/rng-tools` to add the line:

```
HRNGDEVICE=/dev/urandom
```

And finally starting the rng-tools daemon with:

```
sudo /etc/init.d/rng-tools start
```

**source: http://www.howtoforge.com/helping-the-random-number-generator-to-gain-enough-entropy-with-rng-tools-debian-lenny**

### Detailed installation and setup guides

Although some effort is made to provide automatic installation scripts, the following more detailed guides may be
helpful if you are setting up the OSF on a machine already used for other development work, or if you wish to
perform other advanced tasks. If the OSF is already working based on the instructions above, you can skip this section.

#### Using TokUMX

TokuMX is an open-source fork of MongoDB that provides support for transactions in single-sharded environments.
TokuMX supports all MongoDB features as of version 2.4 and adds `beginTransaction`, `rollbackTransaction`, and
`commitTransaction` commands.

##### Installing with Mac OS

```bash
$ brew tap tokutek/tokumx
$ brew install tokumx-bin
```

##### Installing on Ubuntu

```bash
$ apt-key adv --keyserver keyserver.ubuntu.com --recv-key 505A7412
$ echo "deb [arch=amd64] http://s3.amazonaws.com/tokumx-debs $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/tokumx.list
$ apt-get update
$ apt-get install tokumx
```

##### Migrating from MongoDB

TokuMX and MongoDB use different binary formats. To migrate data from MongoDB to TokuMX:

- Back up the MongoDB data
    - `invoke mongodump --path dump`
- Shut down the MongoDB server
- Uninstall MongoDB
- Install TokuMX (see instructions above)
- Restore the data to TokuMX
    - `invoke mongorestore --path dump/osf20130903 --drop`
- Verify that the migrated data are available in TokuMX

#### Using Celery

##### Installing Celery + RabbitMQ

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

##### Starting A Celery Worker

```bash
invoke celery_worker
```

#### Search

Install Elasticsearch to use search features.

##### Mac OSX

```bash
$ brew install elasticsearch
```
_note: Oracle JDK 7 must be installed for elasticsearch to run_

##### Ubuntu

```bash
$ wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.2.1.deb
$ sudo dpkg -i elasticsearch-1.2.1.deb
```

##### Using Elasticsearch
- In your `website/settings/local.py` file, set `SEARCH_ENGINE` to 'elastic'.

```python
SEARCH_ENGINE = 'elastic'
```
- Start the Elasticsearch server and migrate the models.

```bash
$ invoke elasticsearch
$ invoke migrate_search
```
##### Starting a local Elasticsearch server

```bash
$ invoke elasticsearch
```

#### NPM

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

## Common Development Tasks

### Running the shell

To open the interactive Python shell, run:

```bash
$ invoke shell
```

### Running Tests

To run all tests:

```bash
$ invoke test --all
```

To run a certain test method

```bash
$ nosetests tests/test_module.py:TestClass.test_method
```

Run OSF Python tests only:

```bash
$ inv test_osf
```

Run addons Python tests only:

```bash
$ inv test_addons
```

Run Javascript tests:

```bash
$ inv karma
```

By default, `inv karma` will start a Karma process which will re-run your tests every time a JS file is changed.
To do a single run of the JS tests:


```bash
$ inv karma --single
```

By default, Karma will run tests using a PhantomJS headless browser. You can run tests in other browsers like so:

```bash
$ inv karma -b Firefox
```

If you want to run cross browser tests with SauceLabs, use "sauce" parameter:

```bash
$ inv karma --sauce
```

#### Testing Addons

Addons tests are not run by default. To execute addons tests, run

```bash
$ invoke test_addons
```

#### Testing Email


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

### Building front-end assets with webpack

Use the following command to update your requirements and build the asset bundles:

```bash
$ inv assets -dw
```

The -w option puts you in "watch" mode: the script will continue running so that assets will be 
built when a file changes.


### Getting application credentials

Many addons require application credentials (typically an app key and secret) to be able to authenticate through the
OSF. These credentials go in each addon's `local.py` settings file (e.g. `website/addons/dropbox/settings/local.py`).

### COS is Hiring!

Want to help save science? Want to get paid to develop free, open source software? [Check out our openings!](http://cos.io/jobs)

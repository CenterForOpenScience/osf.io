<img src=/docs/waterbutler.png?raw=true" width="25%" style="float:left;">
# WaterButler

`Master` Build Status: [![Build Status](https://travis-ci.org/CenterForOpenScience/waterbutler.svg?branch=master)](https://travis-ci.org/CenterForOpenScience/waterbutler)

`Develop` Build Status: [![Build Status](https://travis-ci.org/CenterForOpenScience/waterbutler.svg?branch=develop)](https://travis-ci.org/CenterForOpenScience/waterbutler)

Docs can be found [here](https://waterbutler.readthedocs.org/en/latest/)

### osf startup commands
*(requires two instances of osf in order to render files)*

```bash
invoke server --port 5001
invoke server
```


### startup commands

In order to run waterbutler, you must have a virtualenv created for waterbutler running python3.3 or higher.  This can be created with the following commands:
```bash
brew install python3 (installs the latest version of python3)
which python3 (prints the path to where python3 is installed)
pip install virtualenv (if you don't already have this)
pip install virtualenvwrapper (if you don't already have this)
mkvirtualenv --python=(path to python3) waterbutler
pip install -U -r requirements.txt
python setup.py develop
invoke server
```

The above code will get the virtualenv up and running for the first time.  After the first time, you can run waterbutler by simply running:
```bash
workon waterbutler
invoke server
```

### testing configuration (optional)

```bash
vim ~/.cos/waterbutler-test.json
```

waterbutler-test.json, e.g.

```json
{
  "OSFSTORAGE_PROVIDER_CONFIG": {
    "HMAC_SECRET": "changeme"
  },
  "SERVER_CONFIG": {
    "ADDRESS": "127.0.0.1",
    "PORT": 7777,
    "DEBUG": true,
    "HMAC_SECRET": "changeme",
    "IDENTITY_API_URL": "http://127.0.0.1:5001/api/v1/files/auth/"
  }
}
```

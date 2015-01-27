# waterbutler

[![Build Status](https://travis-ci.org/CenterForOpenScience/waterbutler.svg?branch=develop)](https://travis-ci.org/CenterForOpenScience/waterbutler)

### osf startup commands
*(requires two instances of osf in order to render files)*

```bash
invoke server --port 5001
invoke server
```


### startup commands

```bash
pip install -U -r requirements.txt
python setup.py develop
invoke server
```

### testing configuration

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

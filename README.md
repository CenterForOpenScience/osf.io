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

### waterbutler-test.json

```json
{
  "OSFSTORAGE_PROVIDER_CONFIG": {
    "HMAC_SECRET": "changeme"
  },
  "SERVER_CONFIG": {
    "ADDRESS": "127.0.0.1",
    "PORT": 7777,
    "DEBUG": true,
    "HMAC_KEY": "changeme",
    "IDENTITY_METHOD": "rest",
    "IDENTITY_API_URL": "http://127.0.0.1:5001/api/v1/files/auth/"
  },
  "LOGGING": {
     "version": 1,
     "disable_existing_loggers": false,
     "formatters": {
       "console": {
         "format": "[%(asctime)s][%(levelname)s][%(name)s]: %(message)s"
       }
     },
     "handlers": {
       "console": {
         "class": "logging.StreamHandler",
         "level": "INFO",
         "formatter": "console"
       },
    },
    "loggers": {
      "": {
        "handlers": ["console"],
        "level": "INFO",
        "propagate": false
      }
    },
    "root": {
      "level": "INFO",
      "handlers": ["console"]
    }
  }
}
```


# OSF API

## Getting started

From the root osf directory:

```bash
pip install -r requirements.txt
# Required for browse-able API
python manage.py collectstatic
invoke server
```

You can run the Django app as a separate process from the OSF Flask app:

```bash
invoke apiserver
```

Browse to `localhost:8000/v2` in your browser to go to the root of the browse-able API.


TODO:

- Fix dev server shutdown when 500 occurs in Django app

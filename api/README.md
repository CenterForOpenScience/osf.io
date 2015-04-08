
## Getting started

From the root osf directory:

```
pip install -r requirements.txt
python api/manage.py collectstatic
invoke server
```

Go to `localhost:5000/api/v2/` in your browser.


TODO:

- Fix dev server shutdown when 500 occurs in Django app

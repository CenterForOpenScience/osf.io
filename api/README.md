
# OSF API

## Getting started

###Installing the OSF

Installation instructions are available on the Readme.md of the root OSF directory on github.
They assume a working knowledge of package managers and the command line.

<<<<<<< HEAD
The [COS Development Docs](http://cosdev.readthedocs.org/) provides detailed information about all aspects of OSF development.
=======
Alternatively, the [COS Development Docs](http://cosdev.readthedocs.org/) provide detailed information about all aspects of OSF development.
>>>>>>> f95375f7b69ea56e8c9cdd2dd8fe3d4de52efe11
This includes [detailed installation instructions](http://cosdev.readthedocs.org/en/latest/osf/setup.html),
a list of [common setup errors](http://cosdev.readthedocs.org/en/latest/osf/setup.html#common-error-messages), and
[other troubleshooting](http://cosdev.readthedocs.org/en/latest/osf/common_problems.html).

The OSF `invoke` script provides several useful commands. For more information, run:

`invoke --list`

<<<<<<< HEAD
##Running the API server
=======
###Running the API server

If you have already installed all of the required services and Python packages, and activated your virtual environment, then you can start a working local API server with the following sequence:
>>>>>>> f95375f7b69ea56e8c9cdd2dd8fe3d4de52efe11

From the root osf directory:

```bash
<<<<<<< HEAD
invoke server
=======
invoke mongo -d
invoke elasticsearch
invoke assets -d
invoke apiserver
>>>>>>> f95375f7b69ea56e8c9cdd2dd8fe3d4de52efe11
```

Both the OSF Flask app and the API Django app will run within the same WSGI app.

Go to `localhost:8000/v2/` in your browser to go to the root of the browse-able API.

Alternatively, you can run the Django app as a separate process from the OSF Flask app:

```bash
invoke apiserver
```

Browse to `localhost:8000/` in your browser to go to the root of the browse-able API.


TODO:

- Fix dev server shutdown when 500 occurs in Django app


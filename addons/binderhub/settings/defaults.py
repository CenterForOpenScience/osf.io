DEFAULT_BINDER_URL = 'https://binder.cs.rcos.nii.ac.jp'

BINDERHUB_OAUTH_CLIENT = dict(
    client_id='AAAA',
    client_secret='BBBB',
    authorize_url='http://192.168.168.167:8585/api/oauth2/authorize',
    token_url='http://192.168.168.167:8585/api/oauth2/token',
    services_url='http://192.168.168.167:8585/api/services',
    scope=['identity'],
)

JUPYTERHUB_TOKEN_EXPIRES_IN_SEC = 3600

JUPYTERHUB_OAUTH_CLIENTS = {
    'http://localhost:8585/': dict(
        admin_api_token='d43ab6030a1b46b39d3233d7fe1843ad',
        client_id='AAAA',
        client_secret='BBBB',
        authorize_url='http://192.168.168.167:12000/hub/api/oauth2/authorize',
        token_url='http://192.168.168.167:12000/hub/api/oauth2/token',
        api_url='http://192.168.168.167:12000/hub/api/',
        scope=['identity'],
    )
}

BINDERHUB_DEPLOYMENT_IMAGES = [
    {
        'url': 'registry.codeocean.com/codeocean/miniconda3:4.8.2-python3.8-ubuntu18.04',
        'name': 'Python (3.8.1, miniconda 4.8.2)',
        'description': 'conda makes this environment a great starting point for installing other languages.',
    },
    {
        'url': 'registry.codeocean.com/codeocean/r-studio:1.2.5019-r4.0.3-ubuntu18.04',
        'name': 'R (4.0.3, RStudio 1.2.5019)',
        'description': 'R is a language and environment for statistical computing and graphics. RStudio is an integrated development environment for R.',
    },
]

JUPYTERHUB_LAUNCHERS = [
    {
        'id': 'default',
        'name': 'Jupyter Notebook',
        'path': None,
        'image': 'jupyter-notebook.png',
    },
    {
        'id': 'lab',
        'name': 'JupyterLab',
        'path': 'lab/',
        'image': 'jupyterlab.png',
    },
    {
        'id': 'rstudio',
        'name': 'RStudio',
        'path': 'rstudio/',
        'image': 'rstudio.png',
    },
]

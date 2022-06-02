DEFAULT_BINDER_URL = 'https://binder.cs.rcos.nii.ac.jp'

BINDERHUB_OAUTH_CLIENT = dict(
    client_id='AAAA',
    client_secret='BBBB',
    authorize_url='https://192.168.168.167:8585/api/oauth2/authorize',
    token_url='https://192.168.168.167:8585/api/oauth2/token',
    services_url='https://192.168.168.167:8585/api/services',
    scope=['identity'],
)

JUPYTERHUB_TOKEN_EXPIRES_IN_SEC = 3600

JUPYTERHUB_OAUTH_CLIENTS = {
    'http://localhost:8585/': dict(
        admin_api_token='CCCC',
        client_id='AAAA',
        client_secret='BBBB',
        authorize_url='http://192.168.168.167:12000/hub/api/oauth2/authorize',
        token_url='http://192.168.168.167:12000/hub/api/oauth2/token',
        api_url='http://192.168.168.167:12000/hub/api/',
        scope=['identity'],
        max_servers=2,
    )
}

BINDERHUB_DEPLOYMENT_IMAGES = [
    {
        'url': 'jupyter/scipy-notebook',
        'name': 'Python',
        'description': 'Notebook Image with Python',
    },
    {
        'url': 'jupyter/r-notebook',
        'name': 'R',
        'description': 'Notebook Image with R',
    },
]

JUPYTERHUB_LAUNCHERS = [
    {
        'id': 'default',
        'name': 'Jupyter Notebook',
        'path': 'tree',
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

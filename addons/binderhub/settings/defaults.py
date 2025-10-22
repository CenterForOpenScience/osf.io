from .matlab_product_name import gen_product_name_list

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
        'deprecated': True,
        'recommended': False,
    },
    {
        'url': 'jupyter/r-notebook',
        'name': 'R',
        'description': 'Notebook Image with R',
        'deprecated': True,
        'recommended': True,
    },
]

MATLAB_RELEASES = [
    'R2024b',
    'R2024a',
    'R2023b',
    'R2023a',
    'R2022b',
    'R2022a',
]

MATLAB_PRODUCTNAMES_MAP = {
    'R2024b': gen_product_name_list('addons/binderhub/settings/mpm_inputs/mpm_input_r2024b.txt'),
    'R2024a': gen_product_name_list('addons/binderhub/settings/mpm_inputs/mpm_input_r2024a.txt'),
    'R2023b': gen_product_name_list('addons/binderhub/settings/mpm_inputs/mpm_input_r2023b.txt'),
    'R2023a': gen_product_name_list('addons/binderhub/settings/mpm_inputs/mpm_input_r2023a.txt'),
    'R2022b': gen_product_name_list('addons/binderhub/settings/mpm_inputs/mpm_input_r2022b.txt'),
    'R2022a': gen_product_name_list('addons/binderhub/settings/mpm_inputs/mpm_input_r2022a.txt'),
}

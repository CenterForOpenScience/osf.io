import os

base_path = str(os.path.dirname(os.path.abspath(__file__)))

# User management & registration
confirm_registrations_by_email = False # Not fully implemented
allow_registration = True
allow_login = True

# External services
try:
    os.environ['OSF_PRODUCTION']
    use_cdn_for_client_libs = True
except KeyError:
    use_cdn_for_client_libs = False

mail_server = 'smtp.sendgrid.net'
mail_username = 'osf-smtp'
mail_password = 'nNtxpg8Q0KqOgR'

static_path = os.path.join(base_path, 'static')

try:
    os.environ['OSF_PRODUCTION']
    cache_path = '/opt/data/osf_cache'
    uploads_path = '/opt/data/uploads'
except:
    cache_path = os.path.join(base_path, 'cache')
    uploads_path = os.path.join(base_path, 'uploads')

try:
    os.environ['OSF_PRODUCTION']
    mongo_uri = 'mongodb://osf:osfosfosfosf0$f@localhost:20771/osf20130903'
except KeyError:
    mongo_uri = 'mongodb://localhost:20771/osf20130903'

#TODO: Configuration should not change between deploys - this should be dynamic.
canonical_domain = 'openscienceframework.org'
cookie_domain = '.openscienceframework.org' # Beaker

# Gravatar options
gravatar_size_profile = 120
gravatar_size_add_contributor = 80

# File upload options
max_upload_size = 1024*1024*250     # In bytes

# File render options
max_render_size = 1024*1024*2.5     # In bytes
img_fmts = ['jpe?g', 'tiff?', 'png', 'gif', 'bmp', 'svg', 'ico']
render_zip = True
render_tar = True
archive_depth = 2               # Set to None for unlimited depth

try:
    os.environ['OSF_PRODUCTION']
    dev_mode = False
except KeyError:
    dev_mode = True

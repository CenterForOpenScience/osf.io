import os

base_path = str(os.path.dirname(os.path.abspath(__file__)))

# User management & registration
confirm_registrations_by_email = False # Not fully implemented
allow_registration = True
allow_login = True

# External services
use_cdn_for_client_libs = False

# Application paths
cache_path = os.path.join(base_path, 'cache')
static_path = os.path.join(base_path, 'static')
# These settings should be overridden by envvars or another method.
uploads_path = os.path.join(base_path, 'uploads')
# uploads_path = '/var/www/openscienceframeworkorg_uploads'
#mongo_uri = 'mongodb://osf:osf@localhost:20771/osf_test'
mongo_uri = 'mongodb://localhost:20771/osf20120530'
# mongo_uri = 'mongodb://osf:osfosfosfosf0$f@localhost:20771/osf_test'

#TODO: Configuration should not change between deploys - this should be dynamic.
canonical_domain = 'openscienceframework.org'
cookie_domain = '.openscienceframework.org' # Beaker

# File upload options #########################
max_upload_size = 250000000     # In bytes

# File render options #########################
max_render_size = 250000000     # In bytes
img_fmts = ['jpe?g', 'tiff?', 'png', 'gif', 'bmp', 'svg', 'ico']
render_zip = True
render_tar = True
archive_depth = 2               # Set to None for unlimited depth

try:
    os.environ['OSF_PRODUCTION']
    dev_mode = False
except KeyError:
    dev_mode = True

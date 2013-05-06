import os

base_path = str(os.path.dirname(os.path.abspath(__file__)))

# User management & registration
confirm_registrations_by_email = False
allow_registration = True
allow_login = True

# External services
use_cdn_for_client_libs = False

# Application paths
cache_path = os.path.join(base_path, 'Cache')
static_path = os.path.join(base_path, 'static')
mongo_uri = 'mongodb://osf:osf@localhost:20771/osf_test'
# mongo_uri = 'mongodb://osf:osfosfosfosf0$f@localhost:20771/osf_test'

#TODO: Configuration should not change between deploys - this should be dynamic.
cookie_domain = '.openscienceframework.org' # Beaker
import os

base_path = str(os.path.dirname(os.path.abspath(__file__)))

# User management & registration
confirm_registrations_by_email = False # Not fully implemented
allow_registration = True
allow_login = True

use_solr = True
solr = 'http://localhost:8983/solr/'

try:
    os.environ['OSF_PRODUCTION']
    debug_mode = False
except KeyError:
    debug_mode = True

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
except KeyError:
    cache_path = os.path.join(base_path, 'cache')
    uploads_path = os.path.join(base_path, 'uploads')

if os.environ.get("OSF_PRODUCTION", False):
    mongo_uri = 'mongodb://osf:osfosfosfosf0$f@localhost:20771/osf20130903'
else:
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

# User activity style
user_activity_max_width = 325

wiki_whitelist = {
    'tags': [
        'a', 'abbr', 'acronym', 'b', 'bdo', 'big', 'blockquote', 'br',
        'center', 'cite', 'code',
        'dd', 'del', 'dfn', 'div', 'dl', 'dt', 'em', 'embed', 'font',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'ins',
        'kbd', 'li', 'object', 'ol', 'param', 'pre', 'p', 'q',
        's', 'samp', 'small', 'span', 'strike', 'strong', 'sub', 'sup',
        'table', 'tbody', 'td', 'th', 'thead', 'tr', 'tt', 'ul', 'u',
        'var', 'wbr',
    ],
    'attributes': [
        'align', 'alt', 'border', 'cite', 'class', 'dir',
        'height', 'href', 'src', 'style', 'title', 'type', 'width',
        'face', 'size', # font tags
        'salign', 'align', 'wmode',
    ],
    # Styles currently used in Reproducibility Project wiki pages
    # TODO: Discuss and possibly delete
    'styles' : [
        'top', 'left', 'width', 'height', 'position',
        'background', 'font-size', 'text-align', 'z-index',
        'list-style',
    ]
}

try:
    os.environ['OSF_PRODUCTION']
    dev_mode = False
except KeyError:
    dev_mode = True

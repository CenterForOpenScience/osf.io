import hashlib
from future.moves.urllib.parse import urlencode

# Adapted from https://github.com/zzzsochi/Flask-Gravatar/blob/master/flaskext/gravatar.py
def gravatar(user, use_ssl=False, d=None, r=None, size=None):

    if use_ssl:
        base_url = 'https://secure.gravatar.com/avatar/'
    else:
        base_url = 'http://www.gravatar.com/avatar/'

    # user can be a User instance or a username string
    username = user.username if hasattr(user, 'username') else user
    hash_code = hashlib.md5(unicode(username).encode('utf-8')).hexdigest()

    url = base_url + '?'

    # Order of query params matters, due to a quirk with gravatar
    params = [
        ('d', 'identicon')
    ]
    if size:
        params.append(('s', size))
    if r:
        params.append(('r', r))
    url = base_url + hash_code + '?' + urlencode(params)

    return url

def profile_image_url(profile_image_filter, *args, **kwargs):
    return filter_providers[profile_image_filter](*args, **kwargs)


filter_providers = {'gravatar': gravatar}

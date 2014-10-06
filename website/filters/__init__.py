import hashlib
import urllib

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

    _locals = locals()
    params = {param: _locals[param] for param in ['r', 'size'] if _locals[param] is not None}
    params['d'] = 'identicon'
    url = base_url + hash_code + '?' + urllib.urlencode(params)

    return url

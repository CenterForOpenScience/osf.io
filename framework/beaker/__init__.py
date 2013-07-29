import website.settings as settings

import framework.flask as web

import beaker.middleware
middleware = beaker.middleware.SessionMiddleware

options = {
    "session.type": "file",
    'session.cookie_expires': False,
    'session.auto': True,
    'session.data_dir': settings.cache_path,
    'session.domain': settings.cookie_domain,
}

def set(x, y=None):
    """
    Usage: 
       set(key, value)
       set((key, value))
       set([(key1, value1), (key2, value2)])
    """
    session = web.request.environ['beaker.session']
    if not isinstance(x, list):
        if y:
            x = [(x, y)]
        else:
            x = [x]
    for i in x:
        session[i[0]] = i[1]
    session.save()

def get(x):
    session = web.request.environ['beaker.session']
    if isinstance(x, list):
        temp_list = []
        for i in x:
            if i in session:
                temp_value = session[i]
            else:
                temp_value = None
            temp_list.append(temp_value)
        return temp_list
    else:
        if x in session:
            temp_value = session[x]
        else:
            temp_value = None
        return temp_value

def invalidate():
    session = web.request.environ['beaker.session']
    session.invalidate()

def delete():
    session = web.request.environ['beaker.session']
    session.delete()

def unset(name):
    session = web.request.environ['beaker.session']
    if not isinstance(name, list):
        name = [name]
    for i in name:
        if i in session.keys():
            del session[i]
    session.save()

def set_previous_url(url=None):
    if url is None:
        url = web.request.referrer
    set('url_previous', url)

def goback():
    url_previous = get('url_previous')
    if url_previous:
        unset('url_previous')
        return web.redirect(url_previous)

session_set = set
session_get = get
import framework

@framework.route('/')
def index():
    return framework.render(filename='index.mako')

@framework.must_be_logged_in
def dashboard(*args, **kwargs):
    user = kwargs['user']
    nodes = [
        {
            'api_url' : node.api_url(),
        }
        for node in user.node__contributed
        if node.category == 'project'
        and not node.is_deleted
        and not node.is_registration
    ]

    return {
        'nodes' : nodes,
    }

@framework.get('/about/')
def about():
    return framework.render(filename="about.mako")

@framework.get('/howosfworks/')
def howosfworks():
    return framework.render(filename="howosfworks.mako")

@framework.get('/reproducibility/')
def reproducibility():
    return framework.redirect('/project/EZcUj/wiki')

@framework.get('/faq/')
def faq():
    return framework.render(filename="faq.mako")

@framework.get('/getting-started/')
def getting_started():
    return framework.render(filename="getting_started.mako")

@framework.get('/explore/')
def explore():
    return framework.render(filename="explore.mako")

@framework.get('/messages/')
@framework.get('/help/')
def soon():
    return framework.render(filename="comingsoon.mako")
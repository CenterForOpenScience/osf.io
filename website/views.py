import framework

@framework.route('/')
def index():
    return framework.render(filename='index.mako')

@framework.route('/dashboard')
@framework.must_be_logged_in
def dashboard(*args, **kwargs):
    user = kwargs['user']
    return framework.render(
        filename='membersIndex.mako', user=user)

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
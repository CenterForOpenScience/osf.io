import framework
import Helper
import Site.Settings

static_folder = Site.Settings.static_path

###############################################################################
# Routes
###############################################################################

@framework.route('/')
def index():
    return framework.render(filename='index.mako')

@framework.route('/dashboard')
@framework.mustBeLoggedIn
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

import Site.Settings as Settings

###############################################################################
# Session
###############################################################################

import framework.Beaker as Session
app = framework.app
app.wsgi_app = Session.Middleware(app.wsgi_app, Session.options)

###############################################################################
# Load models and routes
###############################################################################

Helper.importFiles('framework', 'Model.py')
Helper.importFiles('Site', 'Model.py')

Helper.importFiles('framework', 'Routes.py')
Helper.importFiles('Site', 'Routes.py')

if __name__ == '__main__':

    framework.set_static_folder(
        static_url_path="/static", 
        static_folder=static_folder
    )

    @framework.route('/favicon.ico')
    def favicon():
        return framework.send_from_directory(
            static_folder,
            'favicon.ico', mimetype='image/vnd.microsoft.icon')

    import Site.Settings as Settings
    app.run(port=5000, debug=True)

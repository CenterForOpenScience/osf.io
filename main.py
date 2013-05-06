import Framework
import Helper
import Site.Settings

static_folder = Site.Settings.static_path

###############################################################################
# Routes
###############################################################################

@Framework.route('/')
def index():
    return Framework.render(filename='index.mako')

@Framework.route('/dashboard')
@Framework.mustBeLoggedIn
def dashboard(*args, **kwargs):
    user = kwargs['user']
    return Framework.render(
        filename='membersIndex.mako', user=user)

@Framework.get('/about/')
def about():
    return Framework.render(filename="about.mako")

@Framework.get('/howosfworks/')
def howosfworks():
    return Framework.render(filename="howosfworks.mako")

@Framework.get('/reproducibility/')
def reproducibility():
    return Framework.redirect('/project/EZcUj/wiki')

@Framework.get('/faq/')
def faq():
    return Framework.render(filename="faq.mako")

@Framework.get('/explore/')
def explore():
    return Framework.render(filename="explore.mako")

@Framework.get('/messages/')
@Framework.get('/help/')
def soon():
    return Framework.render(filename="comingsoon.mako")

import Site.Settings as Settings

###############################################################################
# Session
###############################################################################

import Framework.Beaker as Session
app = Framework.app
app.wsgi_app = Session.Middleware(app.wsgi_app, Session.options)

###############################################################################
# Load models and routes
###############################################################################

Helper.importFiles('Framework', 'Model.py')
Helper.importFiles('Site', 'Model.py')

Helper.importFiles('Framework', 'Routes.py')
Helper.importFiles('Site', 'Routes.py')

if __name__ == '__main__':

    Framework.set_static_folder(
        static_url_path="/static", 
        static_folder=static_folder
    )

    @Framework.route('/favicon.ico')
    def favicon():
        return Framework.send_from_directory(
            static_folder,
            'favicon.ico', mimetype='image/vnd.microsoft.icon')

    import Site.Settings as Settings
    app.run(port=5000, debug=True)

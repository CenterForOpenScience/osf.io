import framework
import helper
import website.settings

static_folder = website.settings.static_path

###############################################################################
# Routes
###############################################################################

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

import website.settings as settings

###############################################################################
# Session
###############################################################################

import framework.beaker as session
app = framework.app
app.wsgi_app = session.middleware(app.wsgi_app, session.options)

###############################################################################
# Load models and routes
###############################################################################

helper.import_files('framework', 'model.py')
helper.import_files('website', 'model.py')

helper.import_files('framework', 'routes.py')
helper.import_files('website', 'routes.py')

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

    import website.settings as settings
    app.run(port=5000, debug=True)

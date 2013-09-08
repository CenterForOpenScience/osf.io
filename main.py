import framework
import website.settings

static_folder = website.settings.static_path

import website.settings as settings

###############################################################################
# Session
###############################################################################

import framework.beaker as session
app = framework.app
app.wsgi_app = session.middleware(app.wsgi_app, session.options)

import website.models
import website.routes

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

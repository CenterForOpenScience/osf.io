import framework

import website.settings
import website.models
import website.routes

static_folder = website.settings.static_path

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

    framework.app.run(port=5000, debug=True)

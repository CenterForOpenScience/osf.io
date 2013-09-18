import framework

import website.settings
import website.models
import website.routes

app = framework.app

static_folder = website.settings.static_path

import new_style

if __name__ == '__main__':

    @framework.route('/favicon.ico')
    def favicon():
        return framework.send_from_directory(static_folder,
            'favicon.ico', mimetype='image/vnd.microsoft.icon')

    app.run(port=5000, debug=True)

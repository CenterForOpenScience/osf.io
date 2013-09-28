from new_style import process_rules, render, jsonify, render_mako_string
from framework import app
import view

# Web routes
process_rules(app, [

])

# API routes
process_rules(app, [

        #
        ('/dataverse/get_user_settings_form/', 'get', view.add_user_settings_form, render, {},
            {'template_file':'user_settings/user_settings_form.html', 'renderer':render_mako_string, 'template_dir' : 'website/addons/dataverse/template'}),

        ('/project/<pid>/dataverse/get_node_settings_form/', 'get', view.add_node_settings_form, render, {},
            {'template_file':'node_settings/node_settings_form.html', 'renderer':render_mako_string, 'template_dir' : 'website/addons/dataverse/template'}),
        ('/project/<pid>/node/<nid>/dataverse/get_node_settings_form/', 'get', view.add_node_settings_form, render, {},
            {'template_file':'node_settings/node_settings_form.html', 'renderer':render_mako_string, 'template_dir' : 'website/addons/dataverse/template'}),

        ('/api/v1/dataverse/list_user_settings/', 'get', view.list_user_settings, jsonify, {}, {}),
        ('/api/v1/dataverse/get_user_settings/', 'get', view.add_user_settings, jsonify, {}, {}),
        ('/api/v1/dataverse/add_user_settings/', 'post', view.add_user_settings, jsonify, {}, {}),
        ('/api/v1/dataverse/remove_user_settings/', 'post', view.remove_user_settings, jsonify, {}, {}),

        ('/api/v1/dataverse/get_node_settings/', 'get', view.add_user_settings, jsonify, {}, {}),
        ('/api/v1/project/<pid>/dataverse/add_node_settings/', 'post', view.add_node_settings, jsonify, {}, {}),
        ('/api/v1/project/<pid>/node/<nid>/dataverse/add_node_settings/', 'post', view.add_node_settings, jsonify, {}, {}),
        ('/api/v1/project/<pid>/dataverse/remove_node_settings/', 'post', view.remove_node_settings, jsonify, {}, {}),
        ('/api/v1/project/<pid>/node/<nid>/dataverse/remove_node_settings/', 'post', view.remove_node_settings, jsonify, {}, {}),

        ('/api/v1/dataverse/list_dataverses/', 'get', view.list_dataverses, jsonify, {}, {}),
        ('/api/v1/dataverse/list_studies/', 'get', view.list_studies, jsonify, {}, {}),
        ('/api/v1/project/<pid>/dataverse/list_files/', 'get', view.list_files, jsonify, {}, {}),
        ('/api/v1/project/<pid>/node/<nid>/dataverse/list_files/', 'get', view.list_files, jsonify, {}, {}),
        ('/api/v1/dataverse/add_file/', 'post', view.add_file, jsonify, {}, {}),
        ('/api/v1/dataverse/remove_file/', 'post', view.remove_file, jsonify, {}, {}),
        ('/api/v1/dataverse/update_file/', 'post', view.update_file, jsonify, {}, {}),
        ('/api/v1/dataverse/get_download_url/', 'post', view.get_download_url, jsonify, {}, {}),

    ]
    # prefix='/api/v1/dataverse'
)
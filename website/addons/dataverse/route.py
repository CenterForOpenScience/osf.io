from new_style import process_urls, render, jsonify
from framework import app
import view

# Web routes
process_urls(app, [

])

# API routes
process_urls(app, [

        ('/api/v1/dataverse/get_user_settings/', 'get', view.add_user_settings, jsonify, {}, {}),
        ('/api/v1/dataverse/add_user_settings/', 'post', view.add_user_settings, jsonify, {}, {}),
        ('/api/v1/dataverse/remove_user_settings/', 'post', view.remove_user_settings, jsonify, {}, {}),

        # ('/api/v1/dataverse/get_node_settings/', 'get', view.add_user_settings, jsonify, {}, {}),
        ('/api/v1/dataverse/add_node_settings/', 'post', view.add_node_settings, jsonify, {}, {}),
        # ('/api/v1/dataverse/remove_node_settings/', 'post', view.remove_user_settings, jsonify, {}, {}),

        ('/api/v1/dataverse/list_dataverses/', 'get', view.list_dataverses, jsonify, {}, {}),
        ('/api/v1/dataverse/list_studies/', 'get', view.list_studies, jsonify, {}, {}),
        ('/api/v1/dataverse/list_files/', 'get', view.list_files, jsonify, {}, {}),
        ('/api/v1/dataverse/add_file/', 'post', view.add_file, jsonify, {}, {}),
        ('/api/v1/dataverse/remove_file/', 'post', view.remove_file, jsonify, {}, {}),
        ('/api/v1/dataverse/update_file/', 'post', view.update_file, jsonify, {}, {}),
        ('/api/v1/dataverse/get_download_url/', 'post', view.get_download_url, jsonify, {}, {}),

    ]
    # prefix='/api/v1/dataverse'
)
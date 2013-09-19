from new_style import process_urls, render, jsonify
from framework import app
import view

# Web routes
process_urls(app, [

])

# API routes
process_urls(app, [
        ('/get_user_settings/', 'get', view.add_user_settings, jsonify, {}, {}),
        ('/add_user_settings/', 'post', view.add_user_settings, jsonify, {}, {}),
        ('/remove_user_settings/', 'post', view.remove_user_settings, jsonify, {}, {}),
    ],
    prefix='/api/v1/dataverse'
)
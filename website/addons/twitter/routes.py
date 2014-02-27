
from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views


page_routes = {
    'rules': [

         Rule([
            '/project/<pid>/twitter/settings/',
            '/project/<pid>/node/<nid>/twitter/settings/',
        ], 'post', views.twitter_set_config, json_renderer),

     Rule([
            '/project/<pid>/twitter/update_status/',

        ], 'post', views.twitter_update_status, json_renderer),


        Rule([
            '/project/<pid>/twitter/oauth/',
         '/project/<pid>/node/<nid>/twitter/oauth/',
         ],
            'get', views.oauth_start, OsfWebRenderer('../addons/twitter/templates/myname.mako')),

        Rule([
             '/project/<pid>/twitter/user_auth/',
            '/project/<pid>/node/<nid>/twitter/user_auth/',
            ],
            'get', views.username, OsfWebRenderer('../addons/twitter/templates/myname.mako')),

        Rule([
             '/project/<pid>/twitter/oauth/delete/',
            '/project/<pid>/node/<nid>/twitter/oauth/delete/',
            ],
            'post', views.twitter_oauth_delete_node , json_renderer),
        Rule([
            '/project/<pid>/twitter/widget/',
        ],
            'get', views.twitter_widget, OsfWebRenderer('../addons/twitter/templates/myname.mako')),
],
    'prefix': '/api/v1',

}

settings_routes = {
    'rules': [
        Rule(
            '/sett/'
            , 'get', views.twitter_oauth, OsfWebRenderer('/..addons/twitter/templates/twitter_node_settings.mako')),

    ],
}
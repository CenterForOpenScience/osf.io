
from framework.routing import Rule, json_renderer
from . import views


page_routes = {
    'rules':
        [

        Rule(
            [
                '/project/<pid>/twitter/settings/',
                '/project/<pid>/node/<nid>/twitter/settings/',
            ],
             'post',
             views.twitter_set_config,
             json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/twitter/update_status/',
                '/project/<pid>/node/<nid>/twitter/update_status/'
            ],
            'post',
            views.twitter_update_status,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/twitter/oauth/',
                '/project/<pid>/node/<nid>/twitter/oauth/',
            ],
            'get',
            views.twitter_oauth_start,
            json_renderer
        ),

        Rule(
            [
                '/project/<pid>/twitter/user_auth/',
                '/project/<pid>/node/<nid>/twitter/user_auth/',
            ],
            'get',
            views.twitter_oauth_callback,
            json_renderer
        ),

        Rule(
            [
                '/project/<pid>/twitter/oauth/delete/',
                '/project/<pid>/node/<nid>/twitter/oauth/delete/',
            ],
            'post',
            views.twitter_oauth_delete_node,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/twitter/widget/',
                '/project/<pid>/node/<nid>/twitter/widget/',
            ],
            'get',
            views.twitter_widget,
            json_renderer
        ),

    ],
    'prefix':'/api/v1'
}



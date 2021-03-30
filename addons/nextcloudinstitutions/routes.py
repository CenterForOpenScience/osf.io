# JSON endpoints
from framework.routing import Rule, json_renderer

from addons.nextcloudinstitutions import views

api_routes = {
    'rules': [

        ##### Webhook #####
        Rule(
            ['/addons/nextcloudinstitutions/webhook/'],
            'post',
            views.webhook_nextcloud_app,
            json_renderer
        )
    ],
    'prefix': '/api/v1'
}

"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from website.addons.gitlab import views

settings_routes = {

    'rules': [

        Rule(
            [
                '/project/<pid>/gitlab/file/',
                '/project/<pid>/gitlab/file/<path:path>',
                '/project/<pid>/node/<nid>/gitlab/file/',
                '/project/<pid>/node/<nid>/gitlab/file/<path:path>',
            ],
            'post',
            views.crud.gitlab_upload_file,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/gitlab/file/<path:path>',
                '/project/<pid>/node/<nid>/gitlab/file/<path:path>',
            ],
            'delete',
            views.crud.gitlab_delete_file,
            json_renderer,
        ),

    ],

    'prefix': '/api/v1',

}

api_routes = {

    'rules': [
        
        # TODO: Write me
        # Rule(
        #     [
        #         '/project/<pid>/gitlab/hgrid/',
        #         '/project/<pid>/node/<nid>/gitlab/hgrid/',
        #         '/project/<pid>/gitlab/hgrid/<path:path>/',
        #         '/project/<pid>/node/<nid>/gitlab/hgrid/<path:path>/',
        #     ],
        #     'get',
        #     views.hgrid.gitlab_hgrid_data_contents,
        #     json_renderer,
        # ),
        # Rule(
        #     [
        #         '/project/<pid>/gitlab/hgrid/root/',
        #         '/project/<pid>/node/<nid>/gitlab/hgrid/root/',
        #     ],
        #     'get',
        #     views.hgrid.gitlab_root_folder_public,
        #     json_renderer,
        # ),

        Rule(
            [
                '/project/<pid>/gitlab/file/<path:path>/render/',
                '/project/<pid>/node/<nid>/gitlab/file/<path:path>/render/',
            ],
            'get',
            views.crud.gitlab_get_rendered_file,
            json_renderer,
        ),

    ],
    'prefix': '/api/v1'
}

page_routes = {

    'rules': [

        Rule(
            [
                '/project/<pid>/gitlab/file/<path:path>',
                '/project/<pid>/node/<nid>/gitlab/file/<path:path>',
            ],
            'get',
            views.crud.gitlab_view_file,
            OsfWebRenderer('../addons/gitlab/templates/gitlab_view_file.mako'),
        ),
        Rule(
            [
                '/project/<pid>/gitlab/file/<path:path>/download/',
                '/project/<pid>/node/<nid>/gitlab/file/<path:path>/download/',
            ],
            'get',
            views.crud.gitlab_download_file,
            json_renderer,
        ),

    ],

}

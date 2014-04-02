"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer, notemplate

from website.addons.gitlab import views

api_routes = {

    'rules': [

        Rule(
            [
                '/project/<pid>/gitlab/root/',
                '/project/<pid>/node/<nid>/gitlab/root/',
            ],
             'get',
             views.crud.gitlab_hgrid_root_public,
             json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/gitlab/grid/',
                '/project/<pid>/node/<nid>/gitlab/grid/',
                '/project/<pid>/gitlab/grid/<path:path>/',
                '/project/<pid>/node/<nid>/gitlab/grid/<path:path>/',
            ],
            'get',
            views.crud.gitlab_list_files,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/gitlab/files/',
                '/project/<pid>/gitlab/files/<path:path>',
                '/project/<pid>/node/<nid>/gitlab/files/',
                '/project/<pid>/node/<nid>/gitlab/files/<path:path>',
            ],
            'post',
            views.crud.gitlab_upload_file,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/gitlab/files/<path:path>',
                '/project/<pid>/node/<nid>/gitlab/files/<path:path>',
            ],
            'delete',
            views.crud.gitlab_delete_file,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/gitlab/files/<path:path>/commits/',
                '/project/<pid>/node/<nid>/gitlab/files/<path:path>/commits/',
            ],
            'get',
            views.crud.gitlab_file_commits,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/gitlab/files/<path:path>/render/',
                '/project/<pid>/node/<nid>/gitlab/files/<path:path>/render/',
            ],
            'get',
            views.crud.gitlab_get_rendered_file,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/gitlab/hook/',
                '/project/<pid>/node/<nid>/gitlab/hook/',
            ],
            'post',
            views.hooks.gitlab_hook_callback,
            json_renderer,
        ),


    ],
    'prefix': '/api/v1'
}

page_routes = {

    'rules': [

        Rule(
            [
                '/project/<pid>/gitlab/files/<path:path>',
                '/project/<pid>/node/<nid>/gitlab/files/<path:path>',
            ],
            'get',
            views.crud.gitlab_view_file,
            OsfWebRenderer('../addons/gitlab/templates/gitlab_view_file.mako'),
        ),
        Rule(
            [
                '/project/<pid>/gitlab/files/<path:path>/download/',
                '/project/<pid>/node/<nid>/gitlab/files/<path:path>/download/',
            ],
            'get',
            views.crud.gitlab_download_file,
            notemplate,
        ),

    ],

}

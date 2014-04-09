"""

"""

from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer, notemplate

from website.addons.gitlab import views

from website.addons.gitlab.settings import ROUTE


api_routes = {

    'rules': [

        Rule(
            [
                '/project/<pid>/{route}/root/'.format(route=ROUTE),
                '/project/<pid>/node/<nid>/{route}/root/'.format(route=ROUTE),
            ],
             'get',
             views.crud.gitlab_hgrid_root_public,
             json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/{route}/grid/'.format(route=ROUTE),
                '/project/<pid>/node/<nid>/{route}/grid/'.format(route=ROUTE),
                '/project/<pid>/{route}/grid/<path:path>/'.format(route=ROUTE),
                '/project/<pid>/node/<nid>/{route}/grid/<path:path>/'.format(route=ROUTE),
            ],
            'get',
            views.crud.gitlab_list_files,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/{route}/files/'.format(route=ROUTE),
                '/project/<pid>/{route}/files/<path:path>'.format(route=ROUTE),
                '/project/<pid>/node/<nid>/{route}/files/'.format(route=ROUTE),
                '/project/<pid>/node/<nid>/{route}/files/<path:path>'.format(route=ROUTE),
            ],
            'post',
            views.crud.gitlab_upload_file,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/{route}/files/<path:path>'.format(route=ROUTE),
                '/project/<pid>/node/<nid>/{route}/files/<path:path>'.format(route=ROUTE),
            ],
            'delete',
            views.crud.gitlab_delete_file,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/{route}/files/<path:path>/commits/'.format(route=ROUTE),
                '/project/<pid>/node/<nid>/{route}/files/<path:path>/commits/'.format(route=ROUTE),
            ],
            'get',
            views.crud.gitlab_file_commits,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/{route}/files/<path:path>/render/'.format(route=ROUTE),
                '/project/<pid>/node/<nid>/{route}/files/<path:path>/render/'.format(route=ROUTE),
            ],
            'get',
            views.crud.gitlab_get_rendered_file,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/{route}/hook/'.format(route=ROUTE),
                '/project/<pid>/node/<nid>/{route}/hook/'.format(route=ROUTE),
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
                '/project/<pid>/{route}/files/<path:path>'.format(route=ROUTE),
                '/project/<pid>/node/<nid>/{route}/files/<path:path>'.format(route=ROUTE),
            ],
            'get',
            views.crud.gitlab_view_file,
            OsfWebRenderer('../addons/gitlab/templates/gitlab_view_file.mako'),
        ),
        Rule(
            [
                '/project/<pid>/{route}/files/<path:path>/download/'.format(route=ROUTE),
                '/project/<pid>/node/<nid>/{route}/files/<path:path>/download/'.format(route=ROUTE),
                # Backwards-compatible routes
                '/project/<pid>/{route}/<fid>/download/'.format(route=ROUTE),
                '/project/<pid>/node/<nid>/{route}/<fid>/download/'.format(route=ROUTE),
            ],
            'get',
            views.crud.gitlab_download_file,
            notemplate,
        ),

        # Backwards compatibility with OSF Storage
        Rule(
            [

                # Download file
                '/project/<pid>/osffiles/download/<fid>/',
                '/project/<pid>/node/<nid>/osffiles/download/<fid>/',
                '/project/<pid>/files/<fid>/',
                '/project/<pid>/node/<nid>/files/<fid>/',
                '/project/<pid>/files/download/<fid>/',
                '/project/<pid>/node/<nid>/files/download/<fid>/',
                '/api/v1/project/<pid>/osffiles/<fid>/',
                '/api/v1/project/<pid>/node/<nid>/osffiles/<fid>/',
                '/api/v1/project/<pid>/files/download/<fid>/',
                '/api/v1/project/<pid>/node/<nid>/files/download/<fid>/',

                # Download file by version
                '/project/<pid>/osffiles/download/<fid>/version/<vid>/',
                '/project/<pid>/node/<nid>/osffiles/download/<fid>/version/<vid>/',
                '/project/<pid>/files/<fid>/version/<vid>/',
                '/project/<pid>/node/<nid>/files/<fid>/version/<vid>/',
                '/project/<pid>/files/download/<fid>/version/<vid>/',
                '/project/<pid>/node/<nid>/files/download/<fid>/version/<vid>/',
                '/api/v1/project/<pid>/osffiles/<fid>/version/<vid>/',
                '/api/v1/project/<pid>/node/<nid>/osffiles/<fid>/version/<vid>/',
                '/api/v1/project/<pid>/files/download/<fid>/version/<vid>/',
                '/api/v1/project/<pid>/node/<nid>/files/download/<fid>/version/<vid>/',

            ],
            'get',
            views.crud.gitlab_osffiles_url,
            notemplate,
        )

    ],

}

# -*- coding: utf-8 -*-

from framework.routing import Rule, json_renderer

from website.routes import OsfWebRenderer, notemplate
from website.addons.osfstorage import views


web_routes = {

    'rules': [

        Rule(
            [
                '/project/<pid>/osfstorage/files/<path:path>/',
                '/project/<pid>/node/<nid>/osfstorage/files/<path:path>/',
            ],
            'get',
            views.osf_storage_view_file,
            OsfWebRenderer('../addons/osfstorage/templates/osfstorage_view_file.mako'),
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/files/<path:path>/download/',
                '/project/<pid>/node/<nid>/osfstorage/files/<path:path>/download/',
            ],
            'get',
            views.osf_storage_download_file,
            notemplate,
        ),

    ],
}


api_routes = {

    'prefix': '/api/v1',

    'rules': [

        Rule(
            [
                '/project/<pid>/osfstorage/files/',
                '/project/<pid>/node/<nid>/osfstorage/files/',
                '/project/<pid>/osfstorage/files/<path:path>/',
                '/project/<pid>/node/<nid>/osfstorage/files/<path:path>/',
            ],
            'get',
            views.osf_storage_hgrid_contents,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/files/',
                '/project/<pid>/node/<nid>/osfstorage/files/',
                '/project/<pid>/osfstorage/files/<path:path>/',
                '/project/<pid>/node/<nid>/osfstorage/files/<path:path>/',
            ],
            'post',
            views.osf_storage_request_upload_url,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/files/start/',
                '/project/<pid>/node/<nid>/osfstorage/files/start/',
                '/project/<pid>/osfstorage/files/<path:path>/start/',
                '/project/<pid>/node/<nid>/osfstorage/files/<path:path>/start/',
            ],
            'put',
            views.osf_storage_upload_start_hook,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/files/<path:path>/finish/',
                '/project/<pid>/node/<nid>/osfstorage/files/<path:path>/finish/',
            ],
            'put',
            views.osf_storage_upload_finish_hook,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/files/<path:path>/render/',
                '/project/<pid>/node/<nid>/osfstorage/files/<path:path>/render/',
            ],
            'get',
            views.osf_storage_render_file,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/files/<path:path>/',
                '/project/<pid>/node/<nid>/osfstorage/files/<path:path>/',
            ],
            'delete',
            views.osf_storage_delete_file,
            json_renderer,
        ),

    ],

}


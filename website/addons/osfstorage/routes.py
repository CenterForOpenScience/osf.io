# encoding: utf-8

from framework.routing import Rule, json_renderer

from website.addons.osfstorage import views


api_routes = {

    'prefix': '/api/v1',

    'rules': [

        Rule(
            [
                '/project/<pid>/osfstorage/',
                '/project/<pid>/node/<nid>/osfstorage/',
                '/project/<pid>/osfstorage/<fid>/',
                '/project/<pid>/node/<nid>/osfstorage/<fid>/',
            ],
            'get',
            views.osf_storage_get_metadata,
            json_renderer,
        ),


        Rule(
            [
                '/project/<pid>/osfstorage/<fid>/',
                '/project/<pid>/node/<nid>/osfstorage/<fid>/',
            ],
            'delete',
            views.osf_storage_delete,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/<fid>/download/',
                '/project/<pid>/node/<nid>/osfstorage/<fid>/download/',
            ],
            'get',
            views.osf_storage_download,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/<fid>/revisions/',
                '/project/<pid>/node/<nid>/osfstorage/<fid>/revisions/',
            ],
            'get',
            views.osf_storage_get_revisions,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/<fid>/lineage/',
                '/project/<pid>/node/<nid>/osfstorage/<fid>/lineage/',
            ],
            'get',
            views.osf_storage_get_lineage,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/<fid>/children/',
                '/project/<pid>/node/<nid>/osfstorage/<fid>/children/',
            ],
            'post',
            views.osf_storage_create_child,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/<fid>/children/',
                '/project/<pid>/node/<nid>/osfstorage/<fid>/children/',
            ],
            'get',
            views.osf_storage_get_children,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/hooks/metadata/',
                '/project/<pid>/node/<nid>/osfstorage/hooks/metadata/',
            ],
            'put',
            views.osf_storage_update_metadata,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/hooks/move/',
                '/project/<pid>/node/<nid>/osfstorage/hooks/move',
            ],
            'post',
            views.osf_storage_move_hook,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/hooks/copy/',
                '/project/<pid>/node/<nid>/osfstorage/hooks/copy/',
            ],
            'post',
            views.osf_storage_copy_hook,
            json_renderer,
        ),
    ],

}

# encoding: utf-8

from framework.routing import Rule, json_renderer

from addons.osfstorage import views


api_routes = {

    'prefix': '/api/v1',

    'rules': [

        Rule(
            [
                '/<guid>/osfstorage/',
                '/<guid>/osfstorage/<fid>/',
            ],
            'get',
            views.osfstorage_get_metadata,
            json_renderer,
        ),

        Rule(
            [
                '/<guid>/osfstorage/quota_status/',
            ],
            'get',
            views.osfstorage_get_storage_quota_status,
            json_renderer
        ),

        Rule(
            [
                '/<guid>/osfstorage/<fid>/',
            ],
            'delete',
            views.osfstorage_delete,
            json_renderer,
        ),

        Rule(
            [
                '/<guid>/osfstorage/<fid>/download/',
            ],
            'get',
            views.osfstorage_download,
            json_renderer,
        ),

        Rule(
            [
                '/<guid>/osfstorage/<fid>/revisions/',
            ],
            'get',
            views.osfstorage_get_revisions,
            json_renderer,
        ),

        Rule(
            [
                '/<guid>/osfstorage/<fid>/lineage/',
            ],
            'get',
            views.osfstorage_get_lineage,
            json_renderer,
        ),

        Rule(
            [
                '/<guid>/osfstorage/<fid>/children/',
            ],
            'post',
            views.osfstorage_create_child,
            json_renderer,
        ),

        Rule(
            [
                '/<guid>/osfstorage/<fid>/children/',
            ],
            'get',
            views.osfstorage_get_children,
            json_renderer,
        ),

        Rule(
            [
                '/<guid>/osfstorage/hooks/metadata/',
            ],
            'put',
            views.osfstorage_update_metadata,
            json_renderer,
        ),

        Rule(
            [
                '/<guid>/osfstorage/hooks/move/',
            ],
            'post',
            views.osfstorage_move_hook,
            json_renderer,
        ),

        Rule(
            [
                '/<guid>/osfstorage/hooks/copy/',
            ],
            'post',
            views.osfstorage_copy_hook,
            json_renderer,
        ),

        Rule(
            [
                '/<guid>/osfstorage/<fid>/tags/',
            ],
            'post',
            views.osfstorage_add_tag,
            json_renderer
        ),

        Rule(
            [
                '/<guid>/osfstorage/<fid>/tags/',
            ],
            'delete',
            views.osfstorage_remove_tag,
            json_renderer
        ),
    ],

}

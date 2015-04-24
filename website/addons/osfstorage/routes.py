# encoding: utf-8

from framework.routing import Rule, json_renderer

from website.addons.osfstorage import views
from website.project import views as project_views



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
            views.osf_storage_get_metadata_hook,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/revisions/',
                '/project/<pid>/node/<nid>/osfstorage/revisions/',
            ],
            'get',
            views.osf_storage_get_revisions,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/hooks/crud/',
                '/project/<pid>/node/<nid>/osfstorage/hooks/crud/',
            ],
            'get',
            views.osf_storage_download_file_hook,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/hooks/crud/',
                '/project/<pid>/node/<nid>/osfstorage/hooks/crud/',
            ],
            'put',
            views.osf_storage_update_metadata_hook,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/osfstorage/hooks/crud/',
                '/project/<pid>/node/<nid>/osfstorage/hooks/crud/',
            ],
            'delete',
            views.osf_storage_crud_hook_delete,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/osfstorage/hooks/crud/',
                '/project/<pid>/node/<nid>/osfstorage/hooks/crud/',
            ],
            'post',
            views.osf_storage_upload_file_hook,
            json_renderer,
        ),

         Rule([
            '/project/<pid>/file/addfiletag/<tag>/<guid>/',
            '/project/<pid>/node/<nid>/addfiletag/<tag>/<guid>/',
        ], 'post', project_views.tag.file_addtag, json_renderer),

         Rule([
            '/project/<pid>/file/removefiletag/<tag>/<guid>/',
            '/project/<pid>/node/<nid>/removefiletag/<tag>/<guid>/',
        ], 'post', project_views.tag.file_removetag, json_renderer),


    ],

}

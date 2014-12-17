<%inherit file="project/addon/view_file.mako" />

<%def name="file_versions()">

<div class="scripted" id="revisionScope">

    <ol class="breadcrumb">
        <li><a href="{{ urls.files }}" data-bind="html: node"></a></li>
        <li class="active overflow" data-bind="html: path"></li>
    </ol>

    <a
            class="btn btn-success btn-md"
            data-bind="attr.href: urls.download"
        >Download <i class="icon-download-alt"></i>
    </a>
    <!-- ko if: editable -->
    <button
            class="btn btn-danger btn-md"
            data-bind="click: askDelete"
        >Delete <i class="icon-trash"></i>
    </button>
    <!-- /ko -->


    <table class="table osfstorage-revision-table ">

        <thead>
            <tr>
                <th>Version</th>
                <th>User</th>
                <th>Date</th>
                <th colspan=2>Downloads</th>
            </tr>
        </thead>

        <tbody data-bind="foreach: {data: revisions, as: 'revision'}">
            <tr>
                <td>
                    <a data-bind="attr.href: revision.urls.view">{{ revision.index }}</a>
                </td>
                <td>
                    <a data-bind="attr.href: revision.user.url">{{ revision.user.name }}</a>
                </td>
                <td>{{ revision.displayDate }}</td>
                <td>{{ revision.downloads }}</td>
                <td>
                    <a
                            data-bind="attr.href: revision.urls.download"
                            class="btn btn-primary btn-sm"
                        ><i class="icon-download-alt"></i>
                    </a>
                </td>
            </tr>
        </tbody>

    </table>

    <p data-bind="if: more">
        <a data-bind="click: fetch">More versions...</a>
    </p>

</div>

<script type="text/javascript">
    window.contextVars = $.extend(true, {}, window.contextVars, {
        filePath: '${file_path | h}',
        currentUser: {
            canEdit: ${int(user['can_edit'])}
        },
        node: {
            title: '${node['title'] | h}',
            urls: {
                files:'${files_url}',
                download:'${download_url}',
                delete:'${delete_url}',
                revisions:'${revisions_url}',
            }
        }
    });
</script>

</%def>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
<script src="/static/public/js/osfstorage/file-detail.js"></script>
</%def>

<%inherit file="project/addon/view_file.mako" />

<%def name="file_versions()">

<div class="scripted" id="revisionScope">

    <table class="table osfstorage-revision-table ">

        <thead>
            <tr>
                <th>Version</th>
                <th>User</th>
                <th>Date</th>
                <th></th>
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
                <td>{{ revision.date.local }}</td>
                <td>
                    <a
                            data-bind="attr.href: revision.urls.download"
                            class="btn btn-primary btn-sm"
                        >Download <i class="icon-download-alt"></i>
                    </a>
                </td>
            </tr>
        </tbody>

    </table>

    <p data-bind="if: more">
        <a data-bind="click: fetch">More versions...</a>
    </p>

</div>

<script>
    $script(['/static/addons/osfstorage/storageRevisions.js'], function() {
        var url = '${revisions_url}';
        var revisionTable = new RevisionTable('#revisionScope', url);
    });
</script>

</%def>

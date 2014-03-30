<%inherit file="project/addon/view_file.mako" />


<%def name="file_versions()">
    <table class="table dropbox-revision-table scripted" id="revisionScope">

        <thead>
            <tr>
                <th>Revision</th>
                <th>Date</th>
                <th>Download</th>
            </tr>
        </thead>

        <tbody data-bind="foreach: {data: revisions, as: 'revision'}">
            <!-- Highlight current revision -->
            <tr data-bind="css: {active: revision.rev === $root.currentRevision}"
                class="dropbox-revision">
                <td>
                    <a data-bind="attr: {href: revision.view}">{{ revision.rev }}</a>
                </td>
                <td>{{ revision.modified.local }}</td>
                <td>
                    <a data-bind="attr: {href: revision.download}">
                        <i class="icon-download-alt"></i>
                    </a>
                </td>
            </tr>
        </tbody>

    </table>

    <script>
        $script(["/static/addons/dropbox/revisions.js"], function() {
            var url = '${revisions_url}';
            var revisionTable = new RevisionTable('#revisionScope', url);
        });
    </script>
</%def>

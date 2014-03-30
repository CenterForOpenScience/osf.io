<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>


<%def name="file_versions()">
    <table class="table dropbox-revision-table" id="revisionScope">

        <thead>
            <tr>
                <th>Revision</th>
                <th>Date</th>
                <th>Download</th>
            </tr>
        </thead>

        <tbody data-bind="foreach: revisions">
            <tr class="dropbox-revision">
                <td>
                    <a data-bind="attr: {href: view}, text: rev"></a>
                </td>
                <td data-bind="text: modified.local"></td>
                <td>
                    <a data-bind="attr: {href: download}">
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



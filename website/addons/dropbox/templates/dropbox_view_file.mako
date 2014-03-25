<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>


<%def name="file_versions()">
    <table class="table" id="fileVersionScope">

        <thead>
            <tr>
                <th>Revision</th>
                <th>Date</th>
                <th>Download</th>
            </tr>
        </thead>

        <tbody data-bind="foreach: revisions">
            <tr>
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

    <script src="/addons/static/dropbox/revisions.js"></script>
    <script>
        $(function() {
            var url = '${revisionsUrl}';
            var revisionTable = new RevisionTable('#fileVersionScope', url);
        });
    </script>

</%def>



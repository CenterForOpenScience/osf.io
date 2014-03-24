<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>


<%def name="file_versions()">
    <table class="table" id="fileVersionScope">

        <thead>
            <tr>
                <th>ID</th>
                <th>Date</th>
            </tr>
        </thead>

        <tbody data-bind="foreach: revisions">
            <tr>
                <td data-bind="text: rev"></td>
                <td data-bind="text: modified.local, tooltip: {title: modified.utc}"></td>
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



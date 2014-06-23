<%inherit file="project/addon/view_file.mako" />

<%def name="title()">${file_name}</%def>

<%def name="file_versions()">

    <div class="scripted" id="dataverseScope">
        <table class="table table-striped" id="file-version-history">

            <thead>
            <tr>
                <th>Dataverse</th>
                <th>Study</th>
                <th>Download</th>
            </tr>
            </thead>

            <tbody data-bind="foreach: {data: versions, as: 'version'}">
                <tr>
                    <td>
                        <a data-bind="attr: {href: version.dataverse_url}">
                            {{version.dataverse}}</a>
                    </td>
                    <td>
                        <a data-bind="attr: {href: version.study_url}">
                            {{version.study}}</a>
                    </td>
                    <td>
                        <a href="{{version.download_url}}">
                            <i class="icon-download-alt"></i>
                        </a>
                    </td>
                </tr>
            </tbody>

        </table>

    </div>

    <script>
        $script(["/static/addons/dataverse/view_file.js"], function() {
            var url = '${info_url}';
            var versionTable = new VersionTable('#dataverseScope', url);
        });
    </script>
</%def>
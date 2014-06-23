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

            <tbody>
                <tr data-bind="if: loaded">
                    <td>
                        <a data-bind="attr: {href: dataverse_url}">
                            {{dataverse}}</a>
                    </td>
                    <td>
                        <a data-bind="attr: {href: study_url}">
                            {{study}}</a>
                    </td>
                    <td>
                        <a href="{{download_url}}">
                            <i class="icon-download-alt"></i>
                        </a>
                    </td>
                </tr>
            </tbody>

        </table>

    </div>

    <script>
        $script(["/static/addons/dataverse/dataverseViewFile.js"], function() {
            var url = '${info_url}';
            var dataverseFileTable = new DataverseFileTable('#dataverseScope', url);
        });
    </script>
</%def>
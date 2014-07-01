<%inherit file="project/addon/view_file.mako" />

<%def name="title()">${file_name}</%def>

<%def name="file_versions()">

    <div class="scripted" id="osffileScope">
        <ol class="breadcrumb">
            <li><a href={{files_url}}>{{node_title}}</a></li>
            <li class="active overflow" >{{file_name}}</li>
        </ol>

        <table class="table table-striped" id="file-version-history">

            <thead>
            <tr>
                <th>Version</th>
                <th>Date</th>
                <th>User</th>
                <th colspan=2>Downloads</th>
            </tr>
            </thead>

            <tbody data-bind="foreach: versions">
                <tr>
                    <td>{{version_number}}</td>
                    <td>{{modified_date.local}}</td>
                    <td><a href="{{committer_url}}">{{committer_name}}</a></td>
                    <!-- download count; 'Downloads' column 1 -->
                    <td>{{downloads}}</td>
                    <!-- download url; 'Downloads' column 2 -->
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
        $script(["/static/addons/osffiles/view_file.js"], function() {
            var url = '${info_url}';
            var versionTable = new VersionTable('#osffileScope', url);
        });
    </script>

</%def>

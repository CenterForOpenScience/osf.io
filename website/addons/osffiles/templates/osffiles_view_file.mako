<%inherit file="project/addon/view_file.mako" />

<%def name="title()">${file_name}</%def>

<%def name="file_versions()">
<div id="deletingAlert" class="alert alert-warning fade">
    Deleting your file…
</div>
    <div class="scripted" id="osffileScope">
        <ol class="breadcrumb">
            <li><a href="{{files_page_url}}">{{node_title}}</a></li>
            <li class="active overflow" >{{file_name}}</li>
        </ol>
        <p>
            <a
                    href="{{latest_download_url}}"
                    class="btn btn-success btn-md"
                >Download <i class="icon-download-alt" ></i>
            </a>
            % if user['can_edit'] and 'write' in user['permissions']:
                <a
                        href="#"
                        data-bind="visible: api_url() && !registered(), click: deleteFile"
                        class="btn btn-danger btn-md"
                    >Delete <i class="icon-trash"></i>
                </a>
            % endif
        </p>
        <table class="table table-striped" id="file-version-history">
            <thead>
            <tr>
                <th>Version</th>
                <th>Date</th>
                % if not node['anonymous']:
                    <th>User</th>
                % endif
                <th colspan=2>Downloads</th>
            </tr>
            </thead>
            <tbody data-bind="foreach: versions">
                <tr>
                    <td>{{version_number}}</td>
                    <td>{{modified_date.local}}</td>
                    % if not node['anonymous']:
                        <td><a href="{{committer_url}}">{{committer_name}}</a></td>
                    % endif
                    <!-- download count; 'Downloads' column 1 -->
                    <td>{{downloads}}</td>
                    <!-- download url; 'Downloads' column 2 -->
                    <td>
                        <a href="{{download_url}}">
                            <i class="icon-download-alt btn btn-primary btn-sm"></i>
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

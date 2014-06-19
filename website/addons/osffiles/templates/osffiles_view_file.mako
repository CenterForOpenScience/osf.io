<%inherit file="project/addon/view_file.mako" />

<%def name="title()">${file_name}</%def>

<%def name="file_versions()">

    <ol class="breadcrumb">
        <li><a href="${node['url']}files/">${node['title']}</a></li>
        <li class="active overflow" >${file_name}</li>
    </ol>

    <div class="scripted" id="versionScope">
        <table class="table table-striped" id="file-version-history">


            <thead>
            <tr>
                <th>Version</th>
                <th>Date</th>
                <th>User</th>
                <th colspan=2>Downloads</th>
            </tr>
            </thead>

            <tbody>
            <!-- ko foreach: versions -->
            <tr>
                <td>{{version_number}}</td>
                <td>{{modified_date.local}}</td>
                <td><a href="{{committer_url}}">{{committer_name}}</a></td>
                ## download count; 'Downloads' column 1
                <td>{{downloads}}</td>
                ## download url; 'Downloads' column 2
                <td>
                    <a href="{{download_url}}">
                        <i class="icon-download-alt"></i>
                    </a>
                </td>
            </tr>
            <!-- /ko -->
            </tbody>

        </table>
    </div>

<script>
    $script(["/static/addons/osffiles/versions.js"], function() {
        var url = '${versions_url}';
        var versionTable = new VersionTable('#versionScope', url);
    });
</script>

</%def>

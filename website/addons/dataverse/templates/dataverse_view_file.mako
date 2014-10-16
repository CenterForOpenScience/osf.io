<%inherit file="project/addon/view_file.mako" />

<%def name="title()">${file_name}</%def>

<%def name="file_versions()">

    <ol class="breadcrumb">
         <li><a href="{{files_page_url}}">${node_title}</a></li>
         <li>Dataverse</li>
         <li class="active overflow" >${file_name}</li>
    </ol>

         <p>
             <a href="{{download_url}}" class="btn btn-success btn-lg">Download <i class="icon-download-alt"></i></a>

            % if user['can_edit'] and 'write' in user['permissions']:
                <button data-bind= "click: deleteFile" class="btn btn-danger btn-lg">Delete <i class="icon-trash"></i></button>
            % endif
         </p>


    % if not node['anonymous']:
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
                            <a href="{{download_url}}" class="btn btn-primary btn-sm">
                               Download <i class="icon-download-alt"></i>
                            </a>
                        </td>
                    </tr>
                </tbody>

            </table>

        </div>
    % endif

    <script>
        $script(["/static/addons/dataverse/dataverseViewFile.js"], function() {
            var url = '${info_url}';
            var dataverseFileTable = new DataverseFileTable('#dataverseScope', url);
        });
    </script>
</%def>

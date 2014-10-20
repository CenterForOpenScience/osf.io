<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">
    <div class='scripted' id='s3Scope'>

        <div id="deletingAlert" class="alert alert-warning fade">
            Deleting your file…
        </div>

        % if user['can_edit'] and 'write' in user['permissions']:
            <p>
            % if versions:
                <a href="${versions[0]['download']}" class ="btn btn-success btn-md" download="${file_name}">
                                 Download <i class="icon-download-alt"></i>
                </a>
            % endif
                <a href="#" data-bind="visible: api_url, click: deleteFile" class="btn btn-danger btn-md">
                    Delete <i class="icon-trash"></i>
                </a>
            </p>
        % endif

        <table class="table" id="file-version-history">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Date</th>
                    <th></th>
                </tr>
            </thead>

            <tbody>
                % for version in versions:
                    <tr class="${'active' if version['id'] == current else ''}">
                        <td>
                            <a href="${'?vid=' + version['id']}" title="${version['id']}">
                                ${version['id'][:14]}
                            </a>
                        </td>
                        <td>
                            ${version['date']}
                        </td>
                        <td>
                            <a href="${version['download']}" class ="btn btn-primary btn-sm" download="${file_name}">
                                 <i class="icon-download-alt"></i>
                            </a>
                        </td>
                    </tr>
                %endfor
            </tbody>

        </table>
    </div>
    <script>
        $script(['/static/js/deleteFile.js'], function() {
            var delete_url = '${delete_url}';
            var url = '${info_url}';
            var deleteFile = new DeleteFile('#s3Scope', url, delete_url);
        });
    </script>

</%def>

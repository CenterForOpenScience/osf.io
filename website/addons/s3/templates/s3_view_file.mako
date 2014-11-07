<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">
    <div id='s3Scope'>
    <div id="deletingAlert" class="alert alert-warning fade">
                    Deleting your file…
                </div>


            <p>
                <span id="downloadButtonScope">
                    <a data-bind="attr: {href: downloadURL}"
                        class="btn btn-success btn-md"
                        >Download <i class="icon-download-alt" ></i>
                    </a>
                </span>
                % if user['can_edit'] and 'write' in user['permissions']:
                    <span id="deleteButtonScope" class='scripted'>
                        <a href="#" data-bind="visible: api_url, click: deleteFile" class="btn btn-danger btn-md" >
                            Delete <i class="icon-trash"></i>
                        </a>
                    </span>
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
            var urls = {
                'delete_url': '${delete_url}',
                'files_page_url': '${files_page_url}'
            };
            var deleteFile = new DeleteFile('#deleteButtonScope', urls);
        });
    </script>
    <script>
        $script(['/static/js/downloadFile.js'], function() {
            var download_url = '${download_url}';
            var url = '${info_url}';
            var downloadFile = new DownloadFile('#downloadButtonScope', url, download_url);
        });
    </script>
</%def>

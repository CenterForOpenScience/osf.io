<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">
    <div id='s3Scope' class="scripted">

        <div class="alert alert-warning" data-bind="visible: deleting">
            Deleting your file…
        </div>

            <p>
                % if download_url:
                    <!--download button-->
                    <a class="btn btn-success btn-md" href="${download_url}">
                        Download <i class="icon-download-alt"></i></a>
                % endif
                % if user['can_edit'] and 'write' in user['permissions']:
                    <!--delete button-->
                    <a href="#" data-bind="visible: api_url, click: deleteFile" class="btn btn-danger btn-md" >
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
    <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars, {
            node: {
                urls: {
                    delete_url: '${delete_url}',
                    files_page_url: '${files_page_url}'
                    }
            }
        });
    </script>
    <script src="/static/public/js/s3/file-detail.js"></script>
</%def>

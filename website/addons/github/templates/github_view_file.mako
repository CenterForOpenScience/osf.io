<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">
<div class="scripted" id="githubScope">

    <div class="alert alert-warning" data-bind="visible: deleting">
        Deleting your file…
    </div>

    <ol class="breadcrumb">
        <li class="active overflow"><a href=${files_page_url}>${node['title']}</a></li>
        <li>GitHub</li>
        <li class="active overflow">${file_name}</li>
    </ol>

    <p>
        % if download_url:
             <!--download button-->
             <a class="btn btn-success btn-md" href=${download_url}>
                 Download <i class="icon-download-alt"></i></a>
        % endif

        % if user['can_edit'] and delete_url:
             <!--delete button-->
             <button class="btn btn-danger btn-md" data-bind="click: deleteFile">
                 Delete <i class="icon-trash"></i></button>
        % endif
     </p>


    <table class="table" id="file-version-history">

        <thead>
            <tr>
                <th>Commit</th>
                <th>Date</th>
                % if not node['anonymous']:
                    <th>User</th>
                % endif
                <th></th>
            </tr>
        </thead>

        <tbody>
            % for commit in commits:
                <tr class="${'active' if commit['sha'] == current_sha else ''}">
                    <!-- SHA -->
                    <td>
                        <a href="${commit['view']}" title="${commit['sha']}">
                            ${commit['sha'][:10]}
                        </a>
                    </td>
                    <!-- Commit date -->
                    <td>
                        ${commit['date']}
                    </td>
                    <!-- committer -->
                    % if not node['anonymous']:
                        <td>
                            <a href="mailto:${commit['email']}">
                                ${commit['name']}
                            </a>
                        </td>
                    % endif
                    <td>
                        <a href="${commit['download']}" class="btn btn-primary btn-sm" download="${file_name}">
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
<script src="/static/public/js/github/file-detail.js"></script>
</%def>

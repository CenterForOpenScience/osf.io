<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">

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
                            Download <i class="icon-download-alt"></i>
                        </a>
                    </td>
                </tr>
            %endfor
        </tbody>

    </table>

</%def>

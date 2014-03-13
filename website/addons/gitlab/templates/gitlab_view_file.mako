<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">

    <table class="table" id="file-version-history">

##        <thead>
##            <tr>
##                <th>Commit</th>
##                <th>Date</th>
##                <th>User</th>
##                <th>Download</th>
##            </tr>
##        </thead>
##
##        <tbody>
##            % for commit in commits:
##                <tr class="${'active' if commit['sha'] == current_sha else ''}">
##                    <td>
##                        <a href="${commit['view']}" title="${commit['sha']}">
##                            ${commit['sha'][:10]}
##                        </a>
##                    </td>
##                    <td>
##                        ${commit['date']}
##                    </td>
##                    <td>
##                        <a href="mailto:${commit['email']}">
##                            ${commit['name']}
##                        </a>
##                    </td>
##                    <td>
##                        <a href="${commit['download']}" download="${file_name}">
##                            <i class="icon-download-alt"></i>
##                        </a>
##                    </td>
##                </tr>
##            %endfor
##        </tbody>

    </table>

</%def>

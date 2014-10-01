<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">
    <table class="table" id="file-version-history">

        <thead>
            <tr>
                <th>ID</th>
                <th>Date</th>
                <th>Download</th>
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
                        <a href="${version['download']}" class ="btn btn-lg"download="${file_name}">
                             Download <i class="icon-download-alt"></i>
                        </a>
                    </td>
                </tr>
            %endfor
        </tbody>

    </table>
</%def>

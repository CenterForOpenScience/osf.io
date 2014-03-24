<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>


<%def name="file_versions()">
    <table class="table" id="fileVersionHistory">

        <thead>
            <tr>
                <th>ID</th>
                <th>Date</th>
            </tr>
        </thead>

        <tbody>
            % for revision in revisions:
                <tr>
                    <td>
                        ${revision['rev']}
                    </td>
                    <td>
                        ${revision['modified']}
                    </td>
                </tr>
            %endfor
        </tbody>

    </table>
</%def>

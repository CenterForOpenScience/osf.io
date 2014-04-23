<%inherit file="project/addon/view_file.mako" />

<%def name="title()">${file_name}</%def>

<%def name="file_versions()">

    <ol class="breadcrumb">
        <li><a href="${node['url']}files/">${node['title']}</a></li>
        <li class="active overflow" >${file_name}</li>
    </ol>

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
            % for version in versions:
                <tr>
                    <td>
                        ${version['display_number']}
                    </td>
                    <td>
                        ${version['date_uploaded']}
                    </td>
                    <td>
                        <a href="${version['committer_url']}">
                            ${version['committer_name']}
                        </a>
                    </td>
                    <td>
                        ${version['total']}
                    </td>
                    <td>
                        <a href="${version['download_url']}" download="${version['file_name']}">
                            <i class="icon-download-alt"></i>
                        </a>
                    </td>
                </tr>
            %endfor
        </tbody>

    </table>

</%def>

<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">
<h3>Status: <span class="label label-${'success' if file_status == 'Public' else 'warning'}"> ${file_status}</span></h3>
<h3>Versions: ${file_version} </h3>
<a href="${version_url}">version history</a><br />
<a href="${download_url}">download</a>
</%def>
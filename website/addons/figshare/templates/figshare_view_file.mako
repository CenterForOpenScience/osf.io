<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">
<h3>Status: <span class="label label-${'success' if file_status == 'Public' else 'warning'}"> ${file_status}</span></h3>
% if file_status != 'Public' and parent_type == 'singlefile':
<!--<a id="figsharePublishArticle" class="btn btn-danger">Publish</a><h3>
<script type="text/javascript">
$('#figsharePublishArticle').on('click', function(){
    bootbox.confirm('', function(result){
        if (result){
        var cat = $('#figshareCategory').val();
        $.ajax({
            type: 'POST',
            url: nodeApiUrl+'
            data: JSON.stringify({category:cat}),
            dataType: 'json',
            contentType: 'application/json'
        });
    }});
});
</script>
-->
% endif
%if download_url:
    <p><a href="${download_url}" class="btn-success btn">
    Download <i class="icon-download-alt"></i>
    </a></p>
%endif
%if file_versions:
    <p>Versions: ${file_version}
    <a href="${version_url}">Version History</a></p>
%endif
%if figshare_url and not node['anonymous']:
    <p><a href="${figshare_url}">View on FigShare</a></p>
%endif

%if file_status == 'Public':
    <p>FigShare DOI: <a href="${doi}">${doi}</a></p>
%endif
</%def>


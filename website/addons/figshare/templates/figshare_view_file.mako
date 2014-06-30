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
    <a href="${download_url}">
      <i class="icon-download-alt"></i>
    </a><br />
%endif
%if file_versions:
    Versions: ${file_version}
    <a href="${version_url}">Version History</a><br />
%endif 
%if figshare_url:
    <a href="${figshare_url}">View on FigShare</a><br />
%endif

%if file_status == 'Public':
    FigShare DOI: <a href="${doi}">${doi}</a><br />
%endif
</%def>


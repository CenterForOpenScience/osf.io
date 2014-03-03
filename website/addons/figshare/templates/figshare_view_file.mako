<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">
<h3>Status: <span class="label label-${'success' if file_status == 'Public' else 'warning'}"> ${file_status}</span>
% if file_status != 'Public' and parent_type == 'singlefile':
<a id="figsharePublishArticle" class="btn btn-danger">Publish</a><h3>
<script type="text/javascript">
$('#figsharePublishArticle').on('click', function(){
    bootbox.confirm("Publishing this article is an irreversible operation. Once a FigShare article is published it can never be deleted. Proceed with caution. <br /> Also, FigShare requires some additional info before this article can be published: <br /> <h3><label>Category:</label></h3><select id='figshareCategory'>${figshare_categories}</select>", function(result){
        if (result){
        var cat = $('#figshareCategory').val();
        $.ajax({
            type: 'POST',
            url: nodeApiUrl+'figshare/publish/article/${parent_id}/',
            data: JSON.stringify({category:cat}),
            dataType: 'json',
            contentType: 'application/json'
        });
    }});
});
</script>
% endif
<h3>Versions: ${file_version} </h3>
<a href="${version_url}">version history</a><br />
<a href="${download_url}">download</a>
</%def>


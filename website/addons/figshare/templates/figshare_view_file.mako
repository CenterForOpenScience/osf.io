<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">
<div id="figshareScope">
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

    <ol class="breadcrumb">
        <li><a href=${urls['files']}>${node['title']}</a></li>
        <li>Figshare</li>
        <li class="active overflow">${file_name}</li>
    </ol>

    <p>
            %if file_status == 'Public':
                %if urls['download']:
                <a href="${urls['download']}"
                    class="btn btn-success btn-md">Download <i class="icon-download-alt"></i></a>
                %endif

                <button class="btn btn-danger btn-md disabled" data-toggle="popover" data-trigger="hover" title="Cannot Delete File"
                        data-content="Files published on Figshare cannot be deleted.">
                        Delete <i class="icon-trash"></i></button>
            %endif

            %if file_status != 'Public' and user['can_edit'] and 'write' in user['permissions']:

                <button class="btn btn-success btn-md disabled" data-toggle="popover" data-trigger="hover" title="Cannot Download File"
                        data-content="In order to download private Figshare files and drafts, you will need to log into Figshare.">
                        Download <i class="icon-download-alt"></i></button>

                <a data-bind="click: deleteFile" class="btn btn-danger btn-md">Delete <i class="icon-trash"></i>
               </a>

            %endif
    </p>

%if file_versions:
    <p>Versions: ${file_version}
    <a href="${urls['version']}">Version History</a></p>
%endif
%if figshare_url and not node['anonymous']:
    <p><a href="${urls['figshare']}">View on FigShare</a></p>
%endif

%if file_status == 'Public':
    <p>FigShare DOI: <a href="${doi}">${doi}</a></p>
%endif
</div>

    <script>
        $script(['/static/js/deleteFile.js'], function() {
            var urls = {
                'delete_url': '${urls['delete']}',
                'files_page_url': '${urls['files']}'
            };
            var deleteFile = new DeleteFile('#figshareScope', urls);
        });

         $(function () {
            $("[data-toggle='popover']").popover(({html:true}));
            $("[data-toggle='popover'].disabled").css("pointer-events", "auto")
         });
    </script>

</%def>


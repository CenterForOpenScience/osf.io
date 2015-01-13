<%inherit file="project/addon/view_file.mako" />
<%def name="title()">${file_name}</%def>

<%def name="file_versions()">
<div class="scripted" id="figshareScope">
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

    <div class="alert alert-warning" data-bind="visible: deleting">
        Deleting your file…
    </div>

    <ol class="breadcrumb">
        <li class="active overflow"><a href=${urls['files']}>${node['title']}</a></li>
        <li>Figshare</li>
        <li class="active overflow">${file_name}</li>
    </ol>

    <p>
            <!--download button-->
            <a class="btn btn-success btn-md
                % if file_status == 'Public' and urls['download']:
                    " href="${urls['download']}"
                % else:
                    disabled" data-toggle="popover" data-trigger="hover" title="Cannot Download File"
                        data-content="In order to download private Figshare files and drafts, you will need to log into Figshare."
                % endif
            >Download <i class="icon-download-alt"></i></a>

            <!--delete button-->
            % if user['can_edit']:
                <button class="btn btn-danger btn-md
                    % if file_status != 'Public':
                        " data-bind="click: deleteFile"
                    % else:
                        disabled" data-toggle="popover" data-trigger="hover" title="Cannot Delete File"
                            data-content="Files published on Figshare cannot be deleted."
                    % endif
                >Delete <i class="icon-trash"></i></button>
            % endif
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
   <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars, {
            node: {
                urls: {
                    delete_url: '${urls['delete']}',
                    files_page_url: '${urls['files']}'
                    }
            }
        });
    </script>
</%def>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
<script src="/static/public/js/figshare/file-detail.js"></script>
</%def>

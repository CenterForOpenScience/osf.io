<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Files</%def>

<div class="row">
<div class="col-md-12">
    <div class='help-block'>
        % if 'write' in user['permissions'] and not disk_saving_mode:
            <p>To Upload: Drag files from your desktop into a folder below OR click an upload (<button class="btn btn-default btn-mini" disabled><i class="icon-upload-alt"></i></button>) button.</p>
        % endif
    </div>
</div><!-- end col-md-->

</div><!--end row -->
## TODO: This progressbar is used else where; separate into a template include - it's not used here anymore

<div id="treeGrid" class="filebrowser">
<div class="fangorn-loading"> <i class="icon-spinner fangorn-spin"></i> <p class="m-t-sm"> Loading files... </p> </div>
</div>


<%def name="stylesheets()">
${parent.stylesheets()}
% for stylesheet in tree_css:
<link rel='stylesheet' href='${stylesheet}' type='text/css' />
% endfor
</%def>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
% for script in tree_js:
<script type="text/javascript" src="${script}"></script>
% endfor
<script>
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };


$script.ready(['fangorn'], function() {
    
    $.ajax({
      url:  nodeApiUrl + 'files/grid/'
    })
    .done(function( data ) {
        console.log("data", data);
        var fangornOpts = {
            placement : 'project-files',
            divID: 'treeGrid',
            filesData: data.data

        };
        console.log("fangorn", Fangorn);
        var filebrowser = new Fangorn(fangornOpts);
    });

});


</script>
</%def>

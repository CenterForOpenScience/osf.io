<%inherit file="base.mako"/>
<%def name="title()">Files</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<div class="row">
<div class="col-md-8">
    <div class='help-block'>
        <p>To Upload: Drag files from your desktop into a folder below OR click an upload (<button class="btn btn-default btn-mini" disabled><i class="icon-upload"></i></button>) button.</p>
    </div>
</div><!-- end col-md-->

<div class="col-md-4">
    <input role="search" class="form-control" placeholder="Search files..." type="text" id="fileSearch" autofocus>
</div>
</div><!--end row -->

<div id="filebrowserProgressBar" class="progress progress-striped active">
    <div class="progress-bar"  role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100" style="width: 100%">
        <span class="sr-only">Loading</span>
    </div>
</div>
<div id="myGrid" class="filebrowser hgrid"></div>

</%def>

<%def name="stylesheets()">
% for stylesheet in tree_css:
<link rel='stylesheet' href='${stylesheet}' type='text/css' />
% endfor
</%def>

<%def name="javascript_bottom()">
% for script in tree_js:
<script type="text/javascript" src="${script}"></script>
% endfor
<script src="/static/js/dropzone-patch.js"></script>
<script>
$(function(global) {
// Don't show dropped content if user drags outside grid
global.ondragover = function(e) { e.preventDefault(); };
global.ondrop = function(e) { e.preventDefault(); };

var filebrowser = new Rubeus('#myGrid', {
    data: nodeApiUrl + 'files/grid/',
    searchInput: '#fileSearch'
});

})(window);
</script>
</%def>

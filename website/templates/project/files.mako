<%inherit file="base.mako"/>
<%def name="title()">Files</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<h4>Drag and drop files below to upload.</h4>
<!-- <div class="form-group">
<input placeholder="Search" class='form-control search-input' type='text' id='searchInput'>
</div> -->
<div id="myGrid" class="hgrid"></div>

</%def>

<%def name="stylesheets()">
<link rel="stylesheet" href="/static/vendor/hgrid/hgrid.css" type="text/css" />
<link rel="stylesheet" href="/static/css/osf-hgrid.css" type="text/css" />
</%def>

<%def name="javascript()">
<script src="/static/vendor/dropzone/dropzone.js"></script>
<script src="/static/vendor/hgrid/hgrid.js"></script>
<script src='/static/js/filebrowser.js'></script>
</%def>

<%def name="javascript_bottom()">

% for script in tree_js:
<script type="text/javascript" src="${script}"></script>
% endfor
<script>
(function(global) {

// Don't show dropped content if user drags outside grid
global.ondragover = function(e) { e.preventDefault(); };
global.ondrop = function(e) { e.preventDefault(); };

var gridData = ${grid_data};
global.filebrowser = new FileBrowser('#myGrid', {
    data: gridData,
    // searchInput: '#searchInput'
});

})(window);
</script>
</%def>

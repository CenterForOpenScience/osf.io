<%inherit file="base.mako"/>
<%def name="title()">Files</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<h4>Drag and drop files below to upload.</h4>

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
(function(global) {
// Don't show dropped content if user drags outside grid
global.ondragover = function(e) { e.preventDefault(); };
global.ondrop = function(e) { e.preventDefault(); };

var gridData = ${grid_data};
var filebrowser = new Rubeus('#myGrid', { data: gridData });

})(window);
</script>
</%def>

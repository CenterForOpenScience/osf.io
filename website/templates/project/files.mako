<%inherit file="base.mako"/>
<%def name="title()">Files</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<h4>Drag and drop files below to upload.</h4>
<div id="myGrid" class="hgrid"></div>
</div>

<script type="text/javascript">
    var gridData = ${grid_data};
</script>

<!--[if lte IE 9]>
<script>
    browserComp = false;
    var htmlString = "    <form action='" + gridData[0]['uploadUrl'] + "' method='POST' enctype=multipart/form-data>" +
            "<p><input type=file name=file>" +
            "<input type=submit value=Upload>" +
            "<input type='hidden' name='redirect' value='true' />" +
            "</form>"
    $('#dropZoneHeader').css('display', 'none');
    $('#fallback').html(htmlString);
</script>
<![endif]-->
<script>

// Don't show dropped content if user drags outside grid
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };

</script>
</%def>
<%def name="stylesheets()">
<link rel="stylesheet" href="/static/vendor/hgrid/hgrid.css" type="text/css" />
</%def>

<%def name="javascript()">
<script src="/static/vendor/dropzone/dropzone.js"></script>
<script src="/static/vendor/hgrid/hgrid.js"></script>
% for script in tree_js:
<script type="text/javascript" src="${script}"></script>
% endfor
</%def>

<%def name="javascript_bottom()">
<script src='/static/js/filebrowser.js'></script>
<script>
var filebrowser = new FileBrowser('#myGrid', {
    data: gridData
});
</script>
</%def>

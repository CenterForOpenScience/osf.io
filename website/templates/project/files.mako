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

var extensions = ['3gp', '7z', 'ace', 'ai', 'aif', 'aiff', 'amr', 'asf', 'asx', 'bat', 'bin', 'bmp', 'bup',
    'cab', 'cbr', 'cda', 'cdl', 'cdr', 'chm', 'dat', 'divx', 'dll', 'dmg', 'doc', 'docx', 'dss', 'dvf', 'dwg',
    'eml', 'eps', 'exe', 'fla', 'flv', 'gif', 'gz', 'hqx', 'htm', 'html', 'ifo', 'indd', 'iso', 'jar',
    'jpeg', 'jpg', 'lnk', 'log', 'm4a', 'm4b', 'm4p', 'm4v', 'mcd', 'mdb', 'mid', 'mov', 'mp2', 'mp3', 'mp4',
    'mpeg', 'mpg', 'msi', 'mswmm', 'ogg', 'pdf', 'png', 'pps', 'ps', 'psd', 'pst', 'ptb', 'pub', 'qbb',
    'qbw', 'qxd', 'ram', 'rar', 'rm', 'rmvb', 'rtf', 'sea', 'ses', 'sit', 'sitx', 'ss', 'swf', 'tgz', 'thm',
    'tif', 'tmp', 'torrent', 'ttf', 'txt', 'vcd', 'vob', 'wav', 'wma', 'wmv', 'wps', 'xls', 'xpi', 'zip'];

var grid = new HGrid('#myGrid', {
    data: gridData,
    columns: [
        HGrid.Col.Name,
        HGrid.Col.ActionButtons
    ],
    fetchUrl: function(row) {
        return row.urls.fetch;
    },
    downloadUrl: function(row) {
        return row.urls.download;
    },
    deleteUrl: function(row) {
        return row.urls.delete;
    },
    deleteMethod: 'delete',
    uploads: true,
    uploadUrl: function(row) {
        return row.urls.upload;
    },
    uploadMethod: 'post',
});

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

<%inherit file="base.mako"/>
<%def name="title()">Files</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<div id="myGrid" class="dropzone files-page"></div>
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

var TaskNameFormatter = function(row, cell, value, columnDef, dataContext) {
    var spacer = "<span style='display:inline-block;height:1px;width:" + (18 * dataContext["indent"]) + "px'></span>";
    var link = value;
    if (dataContext.nameExtra) {
        link += ' ' + dataContext.nameExtra;
    }
    if(dataContext.view){
        link = "<a href=" + dataContext['view'] + ">" + link + "</a>";
    }
    if (dataContext['type']=='folder') {
        if (dataContext._collapsed) {
            if (dataContext.can_view !== false) {
                return spacer + " <span class='toggle expand nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span></span><span class='folder folder-open'></span>&nbsp;" + link + "</a>";
            }
            else{
                return spacer + " <span class='toggle nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span></span><span class='folder folder-delete'></span>&nbsp;" + link + "</a>";
            }
        } else {
            if (dataContext.can_view !== false) {
                return spacer + " <span class='toggle collapse nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span><span class='folder folder-close'></span>&nbsp;" + link + "</a>";
            }
            else {
                return spacer + " <span class='toggle nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span><span class='folder folder-delete'></span>&nbsp;" + link + "</a>";
            }
        }
    } else {
        var imageUrl = "/static\/img\/hgrid\/fatcowicons\/file_extension_" + dataContext['ext'] + ".png";
        if(extensions.indexOf(dataContext['ext'])==-1){
            imageUrl = "/static\/img\/hgrid\/file.png";
        }
        var element = spacer + " <span class='toggle'></span><span class='file' style='background: url(" + imageUrl+ ") no-repeat left top;'></span>&nbsp;" + link;
        return element;
    }
};

var UploadBars = function(row, cell, value, columnDef, dataContext) {
    if (!dataContext.uploadBar) {
        if (dataContext.download) {
            var delButton = "<button type='button' class='btn btn-danger btn-mini' onclick='myGrid.deleteItems([" + JSON.stringify(dataContext['uid']) + "])'><i class='icon-trash icon-white'></i></button>"
            var downButton = "<a href=" + dataContext['download'] + "><button type='button' class='btn btn-success btn-mini'><i class='icon-download-alt icon-white'></i></button></a>";
            var buttons = downButton;
            if (dataContext.can_edit) {
                buttons += ' ' + delButton;
            }
            return buttons;
        }
    }
    else{
        var id = dataContext['name'].replace(/[\s\.#\'\"]/g, '');
        return "<div style='height: 20px;' class='progress progress-striped active'><div id='" + id + "'class='progress-bar progress-bar-success' style='width: 0%;'></div></div>";
    }
};

var PairFormatter = function(row, cell, value, columnDef, dataContext) {
    if (value) {
        return value[1];
    }
    return '';
};

browserComp = typeof(browserComp) === 'undefined' ? true : browserComp;
var useDropZone = ${int(user['can_edit'])} && browserComp;

var myGrid = HGrid.create({
    container: "#myGrid",
    info: gridData,
    urlAdd: function(item) {
        if (item) {
            return item.uploadUrl;
        } else {
            return contextVars.uploadUrl;
        }
    },
    url: gridData[0].uploadUrl,
    columns:[
        {id: 'name', name: 'Name', field: 'name', width: 550, cssClass: 'cell-title', formatter: TaskNameFormatter, sortable: true, defaultSortAsc: true},
        {id: 'size', name: 'Size', field: 'size', width: 90, formatter: UploadBars, sortable: true, formatter: PairFormatter}
    ],
    enableCellNavigation: false,
    navigation: false,
    autoHeight: true,
    forceFitColumns: true,
    largeGuide: false,
    dropZone: useDropZone,
    dropZonePreviewsContainer: false,
    rowHeight: 30,
    topCrumb: false,
    dragToRoot: false,
    dragDrop: false,

    // Lazy load settings
    lazyLoad: true,
    // Function that returns the URL for the endpoint to get a folder's contents
    // 'item' in this case is a folder
    itemUrl: function(ajaxSource, item){
        var params = {
            parent: item.uid
        };
        $.each(item.data || {}, function(key, value) {
            if (value)
                params[key] = value;
        });
        return item.lazyLoad + '?' + $.param(params);
    }
});

// Only allow one upload at a time until Git collisions are resolved; see
// issue #196
if (myGrid.dropZoneObj) {
    myGrid.dropZoneObj.options.parallelUploads = 1;
}

myGrid.addColumn({id: 'actions', name: 'Actions', width: 150, sortable: true, formatter: UploadBars});
myGrid.Slick.grid.setSortColumn('name');

myGrid.hGridBeforeUpload.subscribe(function(e, args){
    if (args.parent.can_edit) {
        if (args.parent.maxFilesize && args.item.size > args.parent.maxFilesize) {
            bootbox.alert('File too large for ' + args.parent.addonName + ' add-on. Try a different storage add-on.');
            return false;
        }
        myGrid.removeDraggerGuide();
        var path = args.parent.path.slice();
        path.push(args.item.name);
        var item = {
            name: args.item.name,
            parent_uid: args.parent.uid,
            uid: args.item.name,
            type: 'fake',
            uploadBar: true,
            path: path,
            sortpath: path.join('/'),
            ext: null,
            size: args.item.size.toString()
        };
        var promise = $.when(myGrid.addItem(item));
        var d = $.Deferred();
        promise.done(function() {
            d.resolve(true);
        });
        return d;
    }
    return false;
});

myGrid.hGridBeforeMove.subscribe(function(e, args){
    if (args['insertBefore']==0) {
        return false;
    }
    return true;
});

myGrid.hGridBeforeDelete.subscribe(function(e, args) {
    var item = args.items[0];
    if (item['type'] !== 'fake') {
        var msg = 'Are you sure you want to delete the file "' + item.name + '"?';
        var d = $.Deferred();
        bootbox.confirm(
            msg,
            function(result) {
                if (result) {
                    $.ajax({
                        type: 'DELETE',
                        url: item.delete,
                        data: JSON.stringify(item.data || {}),
                        contentType: 'application/json',
                        dataType: 'json',
                        success: function() {
                            d.resolve(true);
                        },
                        error: function() {
                            bootbox.error('Error deleting file.');
                            d.resolve(false);
                        }
                    });
                } else {
                    d.resolve(false);
                }
            }
        );
        return d;
    }
});

myGrid.hGridAfterNav.subscribe(function (e, args){
    $('#componentName').text(args['name']);
});

myGrid.hGridOnMouseEnter.subscribe(function (e, args){
    var parent = args.e.target.parentNode;
    $(parent).addClass('row-hover');
});

myGrid.hGridOnMouseLeave.subscribe(function (e, args){
    $(myGrid.options.container).find('.row-hover').removeClass('row-hover');
});

myGrid.hGridOnUpload.subscribe(function(e, args){
    var value = {};
    // Check if the server says that the file exists already
    var newSlickInfo = JSON.parse(args.xhr.response)[0];
    // Delete fake item
    var item = myGrid.getItemByValue(myGrid.data, args.name, 'uid');
    myGrid.deleteItems([item['uid']]);
    // If action taken is not null, create new item
    if (newSlickInfo.action_taken !== null) {
        myGrid.addItem(newSlickInfo);
        return true;
    }
    return false;
});

if(myGrid.dropZoneObj){
    myGrid.dropZoneObj.on('error', function(file, errorMessage, xhr){
        if(errorMessage.indexOf('Max filesize')!=-1){
            alert(errorMessage);
            var item = myGrid.getItemByValue(myGrid.data, file.name, 'uid')
            if(item){
                myGrid.deleteItems([item['uid']]);
            }
        }
    });
}

// Prompt user before changing URL if files are uploading
$(window).on('beforeunload', function() {
    if (myGrid.dropZoneObj && myGrid.dropZoneObj.getUploadingFiles().length)
        return 'Uploads(s) still in progress. Are you sure you want to leave this page?';
});

// Don't show dropped content if user drags outside grid
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };

</script>
</%def>
<%def name="stylesheets()">
<link rel="stylesheet" href="/static/css/hgrid-base.css" type="text/css" />
</%def>

<%def name="javascript()">
<script src="/static/vendor/jquery-drag-drop/jquery.event.drag-2.2.js"></script>
<script src="/static/vendor/jquery-drag-drop/jquery.event.drop-2.2.js"></script>
<script src="/static/vendor/dropzone/dropzone.js"></script>
<script src="/static/js/slickgrid.custom.min.js"></script>
<script src="/static/js/hgrid.js"></script>
% for script in tree_js:
    <script type="text/javascript" src="${script}"></script>
% endfor
</%def>

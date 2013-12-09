<%inherit file="base.mako"/>
<%def name="title()">Files</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

%if user['can_edit']:
<div class="container" style="position:relative;">
    <h3 id="dropZoneHeader">Drag and drop (or <a href="#" id="clickable">click here</a>) to upload files into <element id="componentName"></element></h3>
    <div id="fallback"></div>
    <div id="totalProgressActive" style="width: 35%; height: 20px; position: absolute; top: 73px; right: 0;" class>
        <div id="totalProgress" class="progress-bar progress-bar-success" style="width: 0%;"></div>
    </div>
</div>
%endif
<div id="myGridBreadcrumbs" style="margin-top: 10px"></div>
<div id="myGrid" class="dropzone files-page"></div>
</div>

<!--[if lte IE 9]>
<script>
    browserComp = false;
    var htmlString = "    <form action='" + ${info}[0]['uploadUrl'] + "' method='POST' enctype=multipart/form-data>" +
            "<p><input type=file name=file>" +
            "<input type=submit value=Upload>" +
            "<input type='hidden' name='redirect' value='true' />" +
            "</form>"
    $('#dropZoneHeader').css('display', 'none');
    $('#fallback').html(htmlString);
</script>
<![endif]-->
<script>

var extensions = ["3gp", "7z", "ace", "ai", "aif", "aiff", "amr", "asf", "asx", "bat", "bin", "bmp", "bup",
    "cab", "cbr", "cda", "cdl", "cdr", "chm", "dat", "divx", "dll", "dmg", "doc", "docx", "dss", "dvf", "dwg",
    "eml", "eps", "exe", "fla", "flv", "gif", "gz", "hqx", "htm", "html", "ifo", "indd", "iso", "jar",
    "jpeg", "jpg", "lnk", "log", "m4a", "m4b", "m4p", "m4v", "mcd", "mdb", "mid", "mov", "mp2", "mp3", "mp4",
    "mpeg", "mpg", "msi", "mswmm", "ogg", "pdf", "png", "pps", "ps", "psd", "pst", "ptb", "pub", "qbb",
    "qbw", "qxd", "ram", "rar", "rm", "rmvb", "rtf", "sea", "ses", "sit", "sitx", "ss", "swf", "tgz", "thm",
    "tif", "tmp", "torrent", "ttf", "txt", "vcd", "vob", "wav", "wma", "wmv", "wps", "xls", "xpi", "zip"];

var TaskNameFormatter = function(row, cell, value, columnDef, dataContext) {
    value = value.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    var spacer = "<span style='display:inline-block;height:1px;width:" + (18 * dataContext["indent"]) + "px'></span>";
    if (dataContext['type']=='folder') {
        if (dataContext._collapsed) {
            if(dataContext['can_view']!="false"){
                return spacer + " <span class='toggle expand nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span></span><span class='folder folder-open'></span>&nbsp;" + value + "</a>";
            }
            else{
                return spacer + " <span class='toggle nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span></span><span class='folder folder-delete'></span>&nbsp;" + "Private Component" + "</a>";
            }
        } else {
            if(dataContext['can_view']!="false"){
                return spacer + " <span class='toggle collapse nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span><span class='folder folder-close'></span>&nbsp;" + value + "</a>";
            }
            else {
                return spacer + " <span class='toggle nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span><span class='folder folder-delete'></span>&nbsp;" + "Private Component" + "</a>";
            }
        }
    } else {
        var link = value;
        if(dataContext['url']){
            link = "<a href=" + dataContext['url'] + ">" + value + "</a>";
        }
        var imageUrl = "/static\/img\/hgrid\/fatcowicons\/file_extension_" + dataContext['ext'] + ".png";
        if(extensions.indexOf(dataContext['ext'])==-1){
            imageUrl = "/static\/img\/hgrid\/file.png";
        }
                ##        var element = spacer + " <span class='toggle'></span><span class='file-" + dataContext['ext'] + "'></span>&nbsp;" + link;
        var element = spacer + " <span class='toggle'></span><span class='file' style='background: url(" + imageUrl+ ") no-repeat left top;'></span>&nbsp;" + link;
        return element;
    }
};

var UploadBars = function(row, cell, value, columnDef, dataContext) {
    if (!dataContext['uploadBar']){
        var spacer = "<span style='display:inline-block;height:1px;width:30px'></span>";
        if(dataContext['url']){
            var delButton = "<button type='button' class='btn btn-danger btn-mini' onclick='myGrid.deleteItems([" + JSON.stringify(dataContext['uid']) + "])'><i class='icon-trash icon-white'></i></button>"
            var url = dataContext['url'].replace('/files/', '/files/download/');
            url = '/api/v1' + url;
            var downButton = "<a href=" + JSON.stringify(url) + "><button type='button' class='btn btn-success btn-mini'><i class='icon-download-alt icon-white'></i></button></a>";
            if(myGrid.getItemByValue(myGrid.data, dataContext['parent_uid'], 'uid')['can_edit']=='false'){
                return "<div class='col-xs-6' style='padding-left:0;padding-right:0'>" +
                        value +
                        "</div>" +
                        "<div class='hGridButton col-xs-6' style='padding-left:0; padding-right:0; text-align: right; display: inline;'>"
                        + downButton +
                        "</div>";
            }
            else return "<div class='col-xs-6' style='padding-left:0;padding-right:0'>" +
                        value +
                        "</div>" +
                        "<div class='hGridButton col-xs-6' style='padding-left:0; padding-right:0; text-align: right; display: inline;'>" +
                        downButton + " " + delButton +
                        "</div>";
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

var Buttons = function(row, cell, value, columnDef, dataContext) {
##    console.log(myGrid.Slick.grid.getCellNode(myGrid.Slick.dataView.getRowById(dataContext['id']), myGrid.Slick.grid.getColumnIndex("downloads")).parentNode);

};

$('#componentName').text(${info}[0]['name']);

if(typeof(browserComp) === 'undefined'){
    browserComp = true;
}

var useDropZone = ${int(user['can_edit'])} && browserComp;

var myGrid = HGrid.create({
    container: "#myGrid",
    info: ${info},
    urlAdd: function(){
        var ans = {};
        for(var i =0; i<${info}.length; i++){
            if(${info}[i].isComponent==="true") {
                ans[${info}[i]['uid']]= ${info}[i]['uploadUrl'];
            }
        }
        ans[null]=${info}[0]['uploadUrl'];
        return ans;
    },
    url: ${info}[0]['uploadUrl'],
    columns:[
        {id: "name", name: "Name", field: "name", width: 550, cssClass: "cell-title", formatter: TaskNameFormatter, sortable: true, defaultSortAsc: true},
        {id: "date", name: "Date Modified", field: "dateModified", width: 160, sortable: true, formatter: PairFormatter},
        {id: "size", name: "Size", field: "sizeRead", width: 90, formatter: UploadBars, sortable: true, formatter: PairFormatter}
    ],
    enableCellNavigation: false,
    breadcrumbBox: "#myGridBreadcrumbs",
    autoHeight: true,
    forceFitColumns: true,
    largeGuide: false,
    dropZone: useDropZone,
    dropZonePreviewsContainer: false,
    rowHeight: 30,
    navLevel: ${info}[0]['uid'],
    topCrumb: false,
    clickUploadElement: "#clickable",
    dragToRoot: false,
    dragDrop: false
});


myGrid.updateBreadcrumbsBox(myGrid.data[0]['uid']);

myGrid.addColumn({id: "downloads", name: "Downloads", field: "downloads", width: 150, sortable: true, formatter: UploadBars});
##myGrid.addColumn({id: "actions", name: "", field: "actions", width: 80, formatter: Buttons});
myGrid.Slick.grid.setSortColumn("name");

myGrid.hGridBeforeUpload.subscribe(function(e, args){
    if(args.parent['can_edit']=='true'){
        myGrid.removeDraggerGuide();
        var path = args.parent['path'].slice();
        path.push(args.item.name);
        var item = {name: args.item.name, parent_uid: args.parent['uid'], uid: args.item.name, type:"fake", uploadBar: true, path: path, sortpath: path.join("/"), ext: "py", size: args.item.size.toString()};
        var promise = $.when(myGrid.addItem(item));
        promise.done(function(bool){
            return true;
        });
    }
    else return false;
});

myGrid.hGridBeforeMove.subscribe(function(e, args){
    if(args['insertBefore']==0){
        return false;
    }
    return true;
});

myGrid.hGridBeforeDelete.subscribe(function(e, args) {
    if (args['items'][0]['type'] !== 'fake') {
        var msg = 'Are you sure you want to delete the file "' + args['items'][0]['name'] + '"?';
        var d = $.Deferred();
        bootbox.confirm(
            msg,
            function(result) {
                if (result) {
                    var url = '/api/v1' + args['items'][0]['url'].replace('/files/', '/files/delete/');
                    $.post(
                        url
                    ).done(function(response) {
                        if (response['status'] != 'success') {
                            bootbox.alert('Error deleting file');
                            d.resolve(false);
                        } else {
                            d.resolve(true);
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
##    $(myGrid.options.container).find(".row-hover").removeClass("row-hover");
##    $(myGrid.options.container).find(".hGridButton").css('display', 'none');
    var parent = args.e.target.parentNode;
    $(parent).addClass("row-hover");
##    $(parent).find('.hGridButton').css('display', 'inline');
});

myGrid.hGridOnMouseLeave.subscribe(function (e, args){
    $(myGrid.options.container).find(".row-hover").removeClass("row-hover");
##    $(myGrid.options.container).find(".hGridButton").css('display', 'none');
});

myGrid.hGridOnUpload.subscribe(function(e, args){
    var value = {};
    // Check if the server says that the file exists already
    var newSlickInfo = JSON.parse(args.xhr.response)[0];
    // Delete fake item
    var item = myGrid.getItemByValue(myGrid.data, args.name, "uid");
    myGrid.deleteItems([item['uid']]);
    // If action taken is not null, create new item
    if (newSlickInfo['action_taken']!==null){
        myGrid.addItem(newSlickInfo);
        return true;
    }
    return false;
});

if(myGrid.dropZoneObj){
    myGrid.dropZoneObj.on("error", function(file, errorMessage, xhr){
        if(errorMessage.indexOf("Max filesize")!=-1){
            alert(errorMessage);
            var item = myGrid.getItemByValue(myGrid.data, file.name, "uid")
            if(item){
                myGrid.deleteItems([item['uid']]);
            }
        }
    });
}

// Prompt user before changing URL if files are uploading
$(window).on('beforeunload', function() {
    if (myGrid.dropZoneObj.getUploadingFiles().length)
        return 'Uploads(s) still in progress. Are you sure you want to leave this page?';
});

window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };

##var date1=0;
##
##myGrid.dropZoneObj.on("sending", function(file, xhr, formData){
##    date1=Date.now();
##    $('#progressStats').css("display", "inline");
##});
##
##myGrid.dropZoneObj.on("uploadprogress", function(file, progress, bytesSent){
##    var time = (Date.now() - date1) / 1000;
##    var text = "Upload Speed: " + Math.round(bytesSent/time/1024) + " kb/s | Progress: " + progress + "%";
##    $('#progressStats').text(text);
##    console.log("Bytes Sent: " + bytesSent);
##    console.log("Seconds since start: " + time);
##    console.log("Bytes/sec: " + bytesSent/time/1024);
##
##});

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
</%def>

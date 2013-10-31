<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

<% import website.settings %>

<link rel="stylesheet" href="/static/css/hgrid-base.css" type="text/css" />
<script src="/static/js/vendor/jquery.event.drag-2.2.js"></script>
<script src="/static/js/vendor/jquery.event.drop-2.2.js"></script>
<script src="/static/js/vendor/dropzone.js"></script>
<script src="/static/js/slickgrid.custom.min.js"></script>
<script src="/static/js/hgrid.js"></script>

%if user_can_edit:
<div class="container" style="position:relative;">
    <h3 style="max-width: 65%;">Drag and drop (or <a href="#" id="clickable">click here</a>) to upload files into <element id="componentName"></element>!</h3>
    <div id="totalProgressActive" style="width: 35%; position: absolute; top: 4px; right: 0;">
        <div id="totalProgress" class="bar" style="width: 0%;"></div>
    </div>
</div>
%endif
<div id="myGridBreadcrumbs" style="margin-top: 10px"></div>
<div id="myGrid" class="dropzone files-page" style="width: 100%;"></div>
</div>

<script>

var extensions = ["3gp", "7z", "ace", "ai", "aif", "aiff", "amr", "asf", "asx", "bat", "bin", "bmp", "bup",
    "cab", "cbr", "cda", "cdl", "cdr", "chm", "dat", "divx", "dll", "dmg", "doc", "docx", "dss", "dvf", "dwg",
    "eml", "eps", "exe", "fla", "flv", "gif", "gz", "hqx", "htm", "html", "ifo", "indd", "iso", "jar",
    "jpeg", "jpg", "lnk", "log", "m4a", "m4b", "m4p", "m4v", "mcd", "mdb", "mid", "mov", "mp2", , "mp3", "mp4",
    "mpeg", "mpg", "msi", "mswmm", "ogg", "pdf", "png", "pps", "ps", "psd", "pst", "ptb", "pub", "qbb",
    "qbw", "qxd", "ram", "rar", "rm", "rmvb", "rtf", "sea", "ses", "sit", "sitx", "ss", "swf", "tgz", "thm",
    "tif", "tmp", "torrent", "ttf", "txt", "vcd", "vob", "wav", "wma", "wmv", "wps", "xls", "xpi", "zip"];

var TaskNameFormatter = function(row, cell, value, columnDef, dataContext) {
    value = value.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    var spacer = "<span style='display:inline-block;height:1px;width:" + (18 * dataContext["indent"]) + "px'></span>";
    if (dataContext['type']=='folder') {
        if (dataContext._collapsed) {
##            if(myGrid.hasChildren(dataContext['uid']))
##                returner = spacer + " <span class='toggle expand nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span>";
##            else
            if(dataContext['can_view']!="false"){
                return spacer + " <span class='toggle expand nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span></span><span class='folder folder-open'></span>&nbsp;" + value + "</a>";
            }
            else{
                return spacer + " <span class='toggle nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span></span><span class='folder folder-delete'></span>&nbsp;" + value + "</a>";
            }
        } else {
            if(dataContext['can_view']!="false"){
                return spacer + " <span class='toggle collapse nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span><span class='folder folder-close'></span>&nbsp;" + value + "</a>";
            }
            else {
                return spacer + " <span class='toggle nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span><span class='folder folder-delete'></span>&nbsp;" + value + "</a>";
            }
        }
    } else {
        var link = "<a href=" + dataContext['url'] + ">" + value + "</a>";
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
        return value;
    }
    else{
        var id = dataContext['name'].replace(/[\s\.#\'\"]/g, '');
        return "<div class='progress progress-striped active'><div id='" + id + "'class='bar' style='width: 0%;'></div></div>";
    }
};

var Buttons = function(row, cell, value, columnDef, dataContext) {
##    console.log(myGrid.Slick.grid.getCellNode(myGrid.Slick.dataView.getRowById(dataContext['id']), myGrid.Slick.grid.getColumnIndex("downloads")).parentNode);
    if(dataContext['url'] && !dataContext['uploadBar']){
        var delButton = "<button type='button' class='btn btn-danger btn-mini' onclick='myGrid.deleteItems([" + JSON.stringify(dataContext['uid']) + "])'><i class='icon-trash icon-white'></i></button>"
        var url = dataContext['url'].replace('/files/', '/files/download/');
        url = '/api/v1' + url;
        var downButton = "<a href=" + JSON.stringify(url) + "><button type='button' class='btn btn-success btn-mini'><i class='icon-download-alt icon-white'></i></button></a>";
        if(myGrid.getItemByValue(myGrid.data, dataContext['parent_uid'], 'uid')['can_edit']=='false'){
            return downButton;
##            return value + "\t" + downButton;
        }
##        else return value + "\t" + downButton + " " + delButton;
        else return downButton + " " + delButton;

    }
};

$('#componentName').text(${info}[0]['name']);


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
        {id: "size", name: "Size", field: "sizeRead", width: 90, formatter: UploadBars, sortable: true}
    ],
    enableCellNavigation: false,
    breadcrumbBox: "#myGridBreadcrumbs",
    autoHeight: true,
    forceFitColumns: true,
    largeGuide: false,
    dropZone: ${int(user_can_edit)},
    dropZonePreviewsContainer: false,
    rowHeight: 30,
    navLevel: ${info}[0]['uid'],
    topCrumb: false,
    clickUploadElement: "#clickable",
    dragToRoot: false,
    dragDrop: false
});



myGrid.updateBreadcrumbsBox(myGrid.data[0]['uid']);
myGrid.addColumn({id: "downloads", name: "Downloads", field: "downloads", width: 90, sortable: true});
myGrid.addColumn({id: "actions", name: "", field: "actions", width: 70, formatter: Buttons});

myGrid.hGridBeforeUpload.subscribe(function(e, args){
    if(args.parent['can_edit']=='true'){
        myGrid.removeDraggerGuide();
        var path = args.parent['path'].slice();
        path.push("nodefile-" +args.item.name);
        var item = {name: args.item.name, parent_uid: args.parent['uid'], uid: "nodefile-" + args.item.name, type:"fake", uploadBar: true, path: path, sortpath: path.join("/"), ext: "py"};
        myGrid.addItem(item);
        return true;
    }
    else return false;
});


myGrid.hGridAfterUpload.subscribe(function(e, args){
    if(args['success']==true){
        myGrid.deleteItems(["nodefile-" + args.item.name]);
        return true;
    }
    else return false;
});

myGrid.hGridBeforeMove.subscribe(function(e, args){
    if(args['insertBefore']==0){
        return false;
    }
    return true;
});

myGrid.hGridBeforeDelete.subscribe(function(e, args){
    if(args['items'][0]['type']!=='fake'){
        var confirm_delete = confirm("Are you sure you want to delete this file?");
        if (confirm_delete==true){
            var url = '/api/v1' + args['items'][0]['url'].replace('/files/', '/files/delete/');
            $.post(url, function(data) {
                console.log(data);
                if(!data['status']=='success') {
                    alert('Error!');
                    return false;
                } else {
                    return true;
                }
            });
        }
        else{
            return false;
        }
    }
});

myGrid.hGridOnMouseEnter.subscribe(function (e, args){
    $(myGrid.options.container).find(".row-hover").removeClass("row-hover");
    $(args.e.target.parentNode).addClass("row-hover");
});

myGrid.hGridOnMouseLeave.subscribe(function (e, args){
    $(myGrid.options.container).find(".row-hover").removeClass("row-hover");
});

myGrid.hGridOnUpload.subscribe(function(e, args){
            var value = {};
            // Check if the server says that the file exists already
            var newSlickInfo = JSON.parse(args.xhr.response)[0];
            console.log(newSlickInfo);
            if (newSlickInfo['action_taken']===null){
                var item = myGrid.getItemByValue(myGrid.data, args.name, "name");
                myGrid.deleteItems([item['uid']]);
                return false;
            }
            else{
                var item = myGrid.getItemByValue(myGrid.data, newSlickInfo['url'], "url");
                if(item){
                    item['type']='fake';
                    myGrid.deleteItems([item['uid']]);
                }
                myGrid.addItem(newSlickInfo);
                return true;

            }
});

</script>
<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>
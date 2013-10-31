## http://www.webappers.com/2011/10/14/how-to-create-collapsible-tree-menu-with-pure-css/

##<script src="/static/js/vendor/jquery-1.7.min.js"></script>
##<script src="/static/js/vendor/jquery-ui-1.8.16.custom.min.js"></script>
<link rel="stylesheet" href="/static/css/hgrid-base.css" type="text/css" />
<script src="/static/js/vendor/jquery.event.drag-2.2.js"></script>
<script src="/static/js/vendor/jquery.event.drop-2.2.js"></script>
<script src="/static/js/vendor/dropzone.js"></script>
<script src="/static/js/slickgrid.custom.min.js"></script>
<script src="/static/js/hgrid.js"></script>

<div id="myGrid" class="dash-page hgrid" style="width: 100%;"></div>

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

    var myGrid = HGrid.create({
        container: "#myGrid",
        info: ${info},
        columns:[
            {id: "name", name: "Name", field: "name", width: 240, cssClass: "cell-title", formatter: TaskNameFormatter, defaultSortAsc: true}
        ],
        dragDrop: false,
        enableCellNavigation: false,
        dropZone: false,
        autoHeight: true,
        forceFitColumns: true,
        navigation: false
    });

    for (var i=0; i<myGrid.data.length; i++){
        if (myGrid.data[i]['type']=="folder"){
            myGrid.data[i]._collapsed = true;
            myGrid.Slick.dataView.updateItem(myGrid.data[i].id, myGrid.data[i]);
        }
    }
</script>
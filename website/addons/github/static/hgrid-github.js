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
        return spacer + " <span class='toggle'></span><span class='file' style='background: url(" + imageUrl+ ") no-repeat left top;'></span>&nbsp;" + link;
    }
};

var PairFormatter = function(row, cell, value, columnDef, dataContext) {
    if (value) {
        return value[1];
    }
    return '';
};

var DownloadFormatter = function(row, cell, value, columnDef, dataContext) {
    if (value) {
        return '<a href="' + value + '"><button type="button" class="btn btn-success btn-mini"><i class="icon-download-alt icon-white"></i></button></a>';
    }
    return '';
};

var grid = HGrid.create({
    container: "#gitGrid",
    info: gridData,
    url: '',
    columns:[
        {id: "name", name: "Name", field: "name", cssClass: "cell-title", formatter: TaskNameFormatter, sortable: true, defaultSortAsc: true},
        {id: "size", name: "Size", field: "size", formatter: PairFormatter, sortable: true},
        {id: "download", name: "Download", field: "download", formatter: DownloadFormatter, sortable: false}
    ],
    enableCellNavigation: false,
    breadcrumbBox: "#gitCrumb",
    autoHeight: true,
    forceFitColumns: true,
    largeGuide: false,
    dropZone: false,
    rowHeight: 30,
//    navLevel: gridData[0]['uid'],
    topCrumb: false,
    dragToRoot: false,
    dragDrop: false
});

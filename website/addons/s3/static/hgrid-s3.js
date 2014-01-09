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
            return spacer + " <span class='toggle expand nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span></span><span class='folder folder-open'></span>&nbsp;" + value + "</a>";
        } else {
            return spacer + " <span class='toggle collapse nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span><span class='folder folder-close'></span>&nbsp;" + value + "</a>";
        }
    } else {
        var link = value;
        if(dataContext['download']){
            link = "<a href=" + dataContext['download'] + ">" + value + "</a>";
        }
        var imageUrl = "/static\/img\/hgrid\/fatcowicons\/file_extension_" + dataContext['ext'] + ".png";
        if(extensions.indexOf(dataContext['ext'])==-1){
            imageUrl = "/static\/img\/hgrid\/file.png";
        }
        return spacer + " <span class='toggle'></span><span class='file' style='background: url(" + imageUrl+ ") no-repeat left top;'></span>&nbsp;" + link;
    }
};

var grid = HGrid.create({
        container: "#s3Grid",
        info: gridData,
        breadcrumbBox: "#s3Crumbs",
        dropZone: true,
        url: '/',
        
        columns:[
        {id: "name", name: "Name", field: "name", cssClass: "cell-title", formatter: TaskNameFormatter, sortable: true, defaultSortAsc: true},
        {id: "size", name: "Size", field: "size", sortable: true},
        {id: "lastMod", name: "Last Modified", field: "lastMod", sortable: true},
        {id: "version_id", name: "Version", field: "version_id", sortable: true},
        ],
        largeGuide: false,
        enableColumnReorder: false,
            topCrumb: false,
    dragToRoot: false,
    dragDrop: false
});
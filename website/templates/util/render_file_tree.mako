<% import json %>

<div id="myGrid" class="dash-page"></div>

<script type="text/javascript">

$(document).ready(function() {

    var gridData = ${json.dumps(grid_data)};

    var extensions = ["3gp", "7z", "ace", "ai", "aif", "aiff", "amr", "asf", "asx", "bat", "bin", "bmp", "bup",
        "cab", "cbr", "cda", "cdl", "cdr", "chm", "dat", "divx", "dll", "dmg", "doc", "docx", "dss", "dvf", "dwg",
        "eml", "eps", "exe", "fla", "flv", "gif", "gz", "hqx", "htm", "html", "ifo", "indd", "iso", "jar",
        "jpeg", "jpg", "lnk", "log", "m4a", "m4b", "m4p", "m4v", "mcd", "mdb", "mid", "mov", "mp2", "mp3", "mp4",
        "mpeg", "mpg", "msi", "mswmm", "ogg", "pdf", "png", "pps", "ps", "psd", "pst", "ptb", "pub", "qbb",
        "qbw", "qxd", "ram", "rar", "rm", "rmvb", "rtf", "sea", "ses", "sit", "sitx", "ss", "swf", "tgz", "thm",
        "tif", "tmp", "torrent", "ttf", "txt", "vcd", "vob", "wav", "wma", "wmv", "wps", "xls", "xpi", "zip"];

    var TaskNameFormatter = function(row, cell, value, columnDef, dataContext) {
        var spacer = "<span style='display:inline-block;height:1px;width:" + (18 * dataContext["indent"]) + "px'></span>";
        var link = value;
        if (dataContext.iconUrl) {
            link = '<img class="hg-addon-icon" src="' + dataContext.iconUrl + '" /> ' + link;
        }
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
                    return spacer + " <span class='toggle nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span></span><span class='folder folder-delete'></span>&nbsp;" + "Private Component" + "</a>";
                }
            } else {
                if (dataContext.can_view !== false) {
                    return spacer + " <span class='toggle collapse nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span><span class='folder folder-close'></span>&nbsp;" + link + "</a>";
                }
                else {
                    return spacer + " <span class='toggle nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span><span class='folder folder-delete'></span>&nbsp;" + "Private Component" + "</a>";
                }
            }
        } else {
            var imageUrl = "/static\/img\/hgrid\/fatcowicons\/file_extension_" + dataContext['ext'] + ".png";
            if(extensions.indexOf(dataContext['ext'])==-1){
                imageUrl = "/static\/img\/hgrid\/file.png";
            }
            return spacer + " <span class='toggle'></span><span class='file' style='background: url(" + imageUrl+ ") no-repeat left top;'></span>&nbsp;" + link;
        }
    };

    myGrid = HGrid.create({
        container: "#myGrid",
        info: gridData,
        columns:[
            {id: "name", name: "Name", field: "name", width: 550, cssClass: "cell-title", formatter: TaskNameFormatter, sortable: true, defaultSortAsc: true},
        ],
        enableCellNavigation: false,
        forceFitColumns: true,
        dropZone: false,
        dragDrop: false,
        navigation: false,

        // Lazy load settings
        lazyLoad: true,
        // Function that returns the URL for the endpoint to get a folder's contents
        // "item" in this case is a folder
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

});
</script>
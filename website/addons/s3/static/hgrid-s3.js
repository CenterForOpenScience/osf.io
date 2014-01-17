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
        //if(dataContext['download']){
            //This will later be changed into a render function
            link = "<a href=render/" +  dataContext['uid'].replace(' ','&spc').replace('/','&sl') + ">" + value + "</a>";
        //}
        var imageUrl = "/static\/img\/hgrid\/fatcowicons\/file_extension_" + dataContext['ext'] + ".png";
        if(extensions.indexOf(dataContext['ext'])==-1){
            imageUrl = "/static\/img\/hgrid\/file.png";
        }
        return spacer + " <span class='toggle'></span><span class='file' style='background: url(" + imageUrl+ ") no-repeat left top;'></span>&nbsp;" + link;
    }
};


var newFolder = function(dataContext) {
    var message = "Please name your new folder."
     var d = $.Deferred();
    bootbox.prompt(message, function(result)
    {
  if (result) {
                    var url = args['items'][0]['deleteUrl'];
                    $.ajax({
                        url: url,
                        type: 'DELETE',
                        data: JSON.stringify({keyPath: args['items'][0]['s3path']}),
                        contentType: 'application/json',
                        dataType: 'json'
                    }).complete(function() {
                        d.resolve(true);
                    }).error(function() {
                        d.resolve(false);
                    });
                } else {
                    d.resolve(false);
                }
            }
        );
        return d;
    };

var UploadBars = function(row, cell, value, columnDef, dataContext) {
    if (!dataContext['uploadBar']){
        var spacer = "<span style='display:inline-block;height:1px;width:30px'></span>";
        if(dataContext['type']!='folder'){
                var delButton = "<button type='button' class='btn btn-danger btn-mini' onclick='grid.deleteItems([" + JSON.stringify(dataContext['uid']) + "])'><i class='icon-trash icon-white'></i></button>"
                var downButton = '<a href=fetchurl/' + dataContext['uid'].replace(' ','&spc').replace('/','&sl')+ '><button type="button" class="btn btn-success btn-mini"><i class="icon-download-alt icon-white"></i></button></a>';
                if(!can_io)
                    delButton  = "";
                if (!can_dl)
                    downButton = "";
            return "<div align=\"center\">" + downButton + " " + delButton + "</div>";
        }else{
            var newFolderButton = "<button type='button' class='btn btn-success btn-mini' onclick='newFolder([" + JSON.stringify(dataContext['uid']) + "])'><i class='icon-plus icon-white'></i></button>"
            return ''//<div align="center">' +  newFolderButton + "</div>";
        }
            }else{
        var id = dataContext['name'].replace(/[\s\.#\'\"]/g, '');
        return "<div style='height: 20px;' class='progress progress-striped active'><div id='" + id + "'class='progress-bar progress-bar-success' style='width: 0%;'></div></div>";
    }
};


var VersionSelect = function(row, cell, value, columnDef, dataContext) {
    if(dataContext['version_id'] == '--' || dataContext['version_id']=='null')
        return '--';
    else
    {
        var selector = '<select id="VersionSelect">';
        for(var i = dataContext['version_id'].length; i > 0; i--)
        {
            selector += "<option value=" + dataContext['version_id'][i] + ">" + i + "</option>";
        }
        return selector + "</select>";
    }
}


var grid = HGrid.create({
        container: "#s3Grid",
        info: gridData,
        breadcrumbBox: "#s3Crumbs",
        dropZone: true,
        columns:[
        {id: "name", name: "Name", field: "name", cssClass: "cell-title", formatter: TaskNameFormatter, sortable: true, defaultSortAsc: true},
        {id: "lastMod", name: "Last Modified", field: "lastMod", sortable: true},
        {id: "size", name: "Size", field: "size", width: 10, sortable: true},
        //{id: "version_id", name: "Version", field: "version_id", width: 7, formatter: VersionSelect, sortable: true},
        ],
        largeGuide: false,
        enableColumnReorder: false,
        topCrumb: false,
        dragToRoot: false,
        dragDrop: false,
        dropZone: true,
        clickUploadElement: '#s3FormUpload',
        urlAdd: function() {
            var ans = {};
            for (var i = 0; i < gridData.length; i++) {
                if (gridData[i].type == 'folder') {
                    ans[gridData[i]['uid']] = gridData[i]['uploadUrl'];
                }
            }
            ans[null] = gridData[0]['uploadUrl'];
            return ans;
        },
        url: gridData[0]['uploadUrl'],
       // navLevel: gridData[0]['uid'],
        dropZonePreviewsContainer: false,
        rowHeight: 30,
        enableCellNavigation: false,
});

grid.addColumn({id: "download", name: "Delete", field: "download", width: 75, sortable: true, formatter: UploadBars});
grid.updateBreadcrumbsBox(grid.data[0]['uid']);

grid.hGridBeforeDelete.subscribe(function(e, args) {
    if (args['items'][0]['type'] !== 'fake') {
        var msg = 'Are you sure you want to delete the file "' + args['items'][0]['name'] + '"?';
        var d = $.Deferred();
        bootbox.confirm(
            msg,
            function(result) {
                if (result) {
                    var url = args['items'][0]['deleteUrl'];
                    $.ajax({
                        url: url,
                        type: 'DELETE',
                        data: JSON.stringify({keyPath: args['items'][0]['uid']}),
                        contentType: 'application/json',
                        dataType: 'json'
                    }).complete(function() {
                        d.resolve(true);
                    }).error(function() {
                        d.resolve(false);
                    });
                } else {
                    d.resolve(false);
                }
            }
        );
        return d;
    }
});


// Upload callbacks

grid.hGridBeforeUpload.subscribe(function(e, args) {
    grid.removeDraggerGuide();
    var path = args.parent['path'].slice();
    path.push(args.item.name);
    var item = {name: args.item.name, parent_uid: args.parent['uid'], uid: args.item.name, type:"fake", uploadBar: true, path: path, sortpath: path.join("/"), ext: "py", size: args.item.size.toString(),version_id:"current"};
    var promise = $.when(grid.addItem(item));
    promise.done(function(bool){
        return true;
    });
});

grid.hGridOnUpload.subscribe(function(e, args) {
    var value = {};
    // Check if the server says that the file exists already
    var newSlickInfo = JSON.parse(args.xhr.response)[0];
    // Delete fake item
    var item = grid.getItemByValue(grid.data, args.name, "uid");
    grid.deleteItems([item['uid']]);
    // If action taken is not null, create new item
    if (newSlickInfo['action_taken'] !== null) {
        grid.addItem(newSlickInfo);
        return true;
    }
    return false;
});


grid.dropZoneObj.on("addedfile", function (file)
{
  $.ajax({
      url: '/eha9r/s3/getsigned/',
      type: 'POST',
      data: JSON.stringify({name:file.name,type:file.type}),
      contentType: 'application/json',
      dataType: 'json'
        }).complete(function(r) {
            result = JSON.parse(r.responseText);

            xhr = new XMLHttpRequest();

            if (xhr.withCredentials != null) {
                xhr.open('PUT', result.signed_request, true);
            } else if (typeof XDomainRequest !== "undefined") {
                xhr = new XDomainRequest();
                xhr.open(method, url);
            } else {
                xhr = null;
            }
            xhr.onload = function() {
                if (xhr.status === 200) {
                    console.log("completed")
                } else {
                    console.log('Upload error: ' + xhr.status);
                }
            };
            xhr.onerror = function() {
                console.log('XHR error.', file);
            };
            xhr.upload.onprogress = function(e) {
                var percentLoaded;
                if (e.lengthComputable) {
                    percentLoaded = Math.round((e.loaded / e.total) * 100);
                    console.log(percentLoaded)
                }
            };

            type = file.type || 'application/octet-stream';

            xhr.setRequestHeader('Content-Type', type);
            xhr.setRequestHeader('x-amz-acl', 'public-read');
            return xhr.send(file);

        });
})

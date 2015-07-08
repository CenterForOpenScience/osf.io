var $ = require('jquery');
var URI = require('URIjs');
var moment = require('moment');
var ko = require('knockout');

var FilesWidget = require('js/FilesWidget');
var Fangorn = require('js/fangorn');
var $osf = require('js/osfHelpers');

var node = window.contextVars.node;

ko.bindingHandlers.osfUploader = {
    init: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
        var userClick = false;
        var fw = new FilesWidget(
            element.id,
            node.urls.api + 'files/grid/',
            {
                onselectrow: function(item) {
                    userClick = true;
                    this.multiselected([item]);
                    self.preview_value = item.data;
                    this.path = item.data.path;
                    self.files = item.data;

                    var tb = this;
                    var fileurl = "";
                    if (item.data.kind === "file") {
                        var redir = new URI(item.data.nodeUrl);
                        redir.segment("files").segment(item.data.provider).segmentCoded(item.data.path.substring(1));
                        fileurl = redir.toString() + '/';
                        $("#scriptName").html(item.data.name);
                        viewModel.setValue(fileurl);
                    } else {
                        $("#scriptName").html("no file selected");
                        fileurl = "";
                        viewModel.setValue(null);
                    }
                },
                dropzone: {                                           // All dropzone options.
                    url: function(files) {return files[0].url;},
                    clickable : "#" + element.id,
                    addRemoveLinks: false,
                    previewTemplate: '<div></div>',
                    parallelUploads: 1,
                    acceptDirectories: false,
                    fallback: function(){}
                },
                resolveRows: function(item) {
                    var tb = this;
                    item.css = '';
                    userClick 

                    if (item.data.addonFullname !== undefined) {
                        if (item.data.addonFullname !== "OSF Storage") {
                            item.open = false;
                            item.load = false;
                            item.css = "text-muted";
                            item.data.permissions.edit = false;
                            item.data.permissions.view = false;
                            if (!item.data.name.includes(" (Only OSF Storage supported to ensure accurate versioning.)")) {
                                item.data.name = item.data.name + " (Only OSF Storage supported to ensure accurate versioning.)";
                            }
                        } else if (item.depth === 2 && userClick === false && viewModel.value() === null) {
                            tb.multiselected([item]);
                        }
                    }
                    if (item.data.kind === "file" && item.data.provider !== "osfstorage") {
                        item.open = false;
                        item.load = false;
                    }
                    if (viewModel.value() !== null) {
                        var fullPath = viewModel.value().split("/");
                        var path = fullPath[fullPath.length - 2];
                        var correctedPath = "/" + path;
                        if (item.data.kind === "file" && item.data.path === correctedPath) {
                            tb.multiselected([item]);
                            $("#scriptName").html(item.data.name);
                        }
                    }
                    if (tb.isMultiselected(item.id)) {
                        item.css = 'fangorn-selected';
                    }
                    var defaultColumns = [{
                        data: 'name',
                        folderIcons: true,
                        filter: true,
                        custom: Fangorn.DefaultColumns._fangornTitleColumn
                    }];
                    if (item.parentID) {
                        item.data.permissions = item.data.permissions || item.parent().data.permissions;
                        if (item.data.kind === 'folder') {
                            item.data.accept = item.data.accept || item.parent().data.accept;
                        }
                    }

                    if (item.data.uploadState && (item.data.uploadState() === 'pending' || item.data.uploadState() === 'uploading')) {
                        return Fangorn.Utils.uploadRowTemplate.call(tb, item);
                    }

                    var configOption = Fangorn.Utils.resolveconfigOption.call(this, item, 'resolveRows', [item]);
                    return configOption || defaultColumns;
                }
  
            }
        );
        fw.init();
    },
    update: function(element, valueAccessor, allBindings, viewModel, bindingContext) {

    }
};

var Uploader = function(data) {
    
    var self = this;

    $.extend(self, data);
};

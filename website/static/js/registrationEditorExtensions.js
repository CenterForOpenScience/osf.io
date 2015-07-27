var $ = require('jquery');
var URI = require('URIjs');
var moment = require('moment');
var ko = require('knockout');
var m = require('mithril');

var FilesWidget = require('js/filesWidget');
var Fangorn = require('js/fangorn');
var $osf = require('js/osfHelpers');

var node = window.contextVars.node;

var NO_FILE = 'no file selected';

var limitOsfStorage = function(item) {
    if (item.data.provider !== undefined && item.data.provider !== 'osfstorage') {
        item.open = false;
        item.load = false;
        item.css = 'text-muted';
        item.data.permissions = item.data.permissions || {};
        item.data.permissions.edit = false;
        item.data.permissions.view = false;
        if (item.data.name.indexOf(' (Only OSF Storage supported to ensure accurate versioning.)') === -1) {
            item.data.name = item.data.name + ' (Only OSF Storage supported to ensure accurate versioning.)';
        }
    }
};

var filePicker;
var osfUploader = function(element, valueAccessor, allBindings, viewModel, bindingContext) {
    viewModel.showUploader(true);

    var $root = bindingContext.$root;
    $root.currentQuestion.subscribe(function(question) {
        if (filePicker) {
            // A hack to flush the old mithril controller.
            // It's unclear to me exactly why this is happening (after 3hrs), but seems
            // to be a KO-mithril interaction. We're programattically changing the div 
            // containing mithril mountings, and for some reason old controllers (and
            // their bound settings) are persisting and being reused. This call 
            // explicity removes the old controller.
            // see: http://lhorie.github.io/mithril/mithril.component.html#unloading-components
            m.mount(document.getElementById(filePicker.fangornOpts.divID), null);

            filePicker.destroy();
            filePicker = null;
        }
    }, null, 'beforeChange');

    var fw = new FilesWidget(
        element.id,
        node.urls.api + 'files/grid/', {
            dropzone: {
                url: function(files) {
                    return files[0].url;
                },
                clickable: '#' + element.id,
                addRemoveLinks: false,
                previewTemplate: '<div></div>',
                parallelUploads: 1,
                acceptDirectories: false
            },
            onselectrow: function(item) {
                if (item.kind === 'file') {
                    viewModel.value(item.data.path);
                    viewModel.selectedFileName(item.data.name);
                    item.css = 'fangorn-selected';
                } else {
                    viewModel.value('');
                    viewModel.selectedFileName(NO_FILE);
                }
            },
            resolveRows: function(item) {
                var tb = this;
                item.css = '';

                limitOsfStorage(item);

                if (viewModel.value() !== null) {
                    if (item.data.path === viewModel.value()) {
                        item.css = 'fangorn-selected';
                    }
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
            },
            lazyLoadOnLoad: function(tree, event) {
                limitOsfStorage(tree);

                tree.children.forEach(function(item) {
                    limitOsfStorage(item);

                    if (viewModel.value() !== null) {
                        if (item.data.path === viewModel.value()) {
                            item.css = 'fangorn-selected';
                            viewModel.selectedFileName(item.data.name);
                        }
                    }
                    Fangorn.Utils.inheritFromParent(item, tree);
                });
                Fangorn.Utils.resolveconfigOption.call(this, tree, 'lazyLoadOnLoad', [tree, event]);
                Fangorn.Utils.reapplyTooltips();

                if (tree.depth > 1) {
                    Fangorn.Utils.orderFolder.call(this, tree);
                }
            }
        });
    filePicker = fw; 
    fw.init(); 
    viewModel.showUploader(false);
};

ko.bindingHandlers.osfUploader = {
    init: osfUploader
};

var Uploader = function(data) {

    var self = this;
    self._orig = data;

    self.selectedFileName = ko.observable('no file selected');
    self.filePicker = null;

    $.extend(self, data);
};

module.exports = {
    Uploader: Uploader,
    osfUploader: osfUploader,
    limitOsfStorage: limitOsfStorage
};

var $ = require('jquery');
var ko = require('knockout');
var m = require('mithril');
var bootbox = require('bootbox');

var FilesWidget = require('js/filesWidget');
var Fangorn = require('js/fangorn');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');
var ContribAdder = require('js/contribAdder');

var node = window.contextVars.node;

var NO_FILE = 'No file selected';

var limitContents = function(item) {
    if (item.data.provider !== undefined && item.data.provider !== 'osfstorage' || item.data.isPointer) {
        item.open = false;
        item.load = false;
        item.css = 'text-muted';
        item.data.permissions = item.data.permissions || {};
        item.data.permissions.edit = false;
        item.data.permissions.view = false;
        if (item.data.isPointer) {
            if (item.data.name.indexOf(' (Linked content is not allowed.)') === -1) {
                item.data.name = item.data.name + ' (Linked content is not allowed.)';
            }
        }
        else if (item.data.name.indexOf(' (Only OSF Storage supported to ensure accurate versioning.)') === -1) {
            item.data.name = item.data.name + ' (Only OSF Storage supported to ensure accurate versioning.)';
        }
    }
};

var filePicker;
var osfUploader = function(element, valueAccessor, allBindings, viewModel, bindingContext) {
    viewModel.showUploader(true);

    var $root = bindingContext.$root;
    $root.currentPage.subscribe(function(question) {
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
                    viewModel.selectedFile(item);
                    item.css = 'fangorn-selected';
                } else {
                    viewModel.value(NO_FILE);
                    viewModel.selectedFile(null);
                }
            },
            resolveRows: function(item) {
                var tb = this;
                item.css = '';

                limitContents(item);

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

                var configOption = Fangorn.Utils.resolveconfigOption.call(this, item, 'resolveRows', [item]);
                return configOption || defaultColumns;
            },
            lazyLoadOnLoad: function(tree, event) {
                limitContents(tree);

                tree.children.forEach(function(item) {
                    limitContents(item);

                    if (viewModel.value() !== null) {
                        if (item.data.path === viewModel.value()) {
                            item.css = 'fangorn-selected';
                            item.data.nodeId = tree.data.nodeId;
                            viewModel.selectedFile(item);
                        }
                    }
                    Fangorn.Utils.inheritFromParent(item, tree);
                });
                Fangorn.Utils.resolveconfigOption.call(this, tree, 'lazyLoadOnLoad', [tree, event]);
                Fangorn.Utils.reapplyTooltips();

                if (tree.depth > 1) {
                    Fangorn.Utils.orderFolder.call(this, tree);
                }
            },
            links: false
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

    self.selectedFile = ko.observable(null);
    self.selectedFile.subscribe(function(file) {
        if (file) {
            data.extra({
                selectedFileName: file.data.name,
                viewUrl: '/project/' + file.data.nodeId + '/files/osfstorage' + file.data.path,
                hasSelectedFile: true
            });
        }
        else {
            data.extra({
                selectedFileName: 'no file selected'
            });
            data.value('no file selected');
        }
    });
    self.hasSelectedFile = ko.computed(function() {
        return !!(data.extra().viewUrl);
    });
    self.unselectFile = self.selectedFile.bind(null, null);

    self.filePicker = null;

    self.preview = function() {
        var value = data.value();
        if (!value || value === 'no file selected') {
            return 'no file selected';
        }
        else {
            var extra = data.extra();
            return $('<a target="_blank" href="' + extra.viewUrl + '">' + extra.selectedFileName + '</a>');
        }
    };

    $.extend(self, data);
};

var AuthorImport = function(data, $root) {
    var self = this;
    self.question = data;

    self.makeContributorsRequest = function() {
        var self = this;
        var contributorsUrl = window.contextVars.node.urls.api + 'get_contributors/';
        return $.getJSON(contributorsUrl);
    };
    self.getContributors = function() {
        var self = this;
        return self.makeContributorsRequest()
            .then(function(data) {
                return $.map(
                    data.contributors, function(c) { return c.fullname; }
                ).join(', ');
            }).fail(function() {
                $osf.growl('Could not retrieve contributors.', 'Please refresh the page or ' +
                           'contact <a href="mailto: support@cos.io">support@cos.io</a> if the ' +
                           'problem persists.');
            });
    };
    self.getContributors().done(function(data) {
        self.value(data);
    });
    self.preview = function() {
        return self.value();
    };
    var callback = function(data) {
        self.value(
            $.map(data.contributors, function(c){ return c.fullname; })
                .join(', '));
    };
    var adder = new ContribAdder(
        '#addContributors',
        node.title,
        node.id,
        null,
        null,
        {async: true, callback: callback}
    );

    $.extend(self, data);
};

module.exports = {
    AuthorImport: AuthorImport,
    Uploader: Uploader,
    osfUploader: osfUploader,
    limitContents: limitContents
};

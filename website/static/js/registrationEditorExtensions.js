var $ = require('jquery');
var ko = require('knockout');
var m = require('mithril');
var bootbox = require('bootbox');

var FilesWidget = require('js/filesWidget');
var Fangorn = require('js/fangorn').Fangorn;
var $osf = require('js/osfHelpers');
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
var filesWidgetCleanUp = [];
var osfUploader = function(element, valueAccessor, allBindings, viewModel, bindingContext) {
    viewModel.showUploader(true);
    viewModel.toggleUploader = function() {
        this.showUploader(!this.showUploader());
    };


    var $root = bindingContext.$root;
    $root.currentPage.subscribe(function(question) {
        if (filePicker) {
            // A hack to flush the old mithril controller.
            // It's unclear to me exactly why this is happening (after 3hrs), but seems
            // to be a KO-mithril interaction. We're programmatically changing the div
            // containing mithril mountings, and for some reason old controllers (and
            // their bound settings) are persisting and being reused. This call
            // explicity removes the old controller.
            // see: http://lhorie.github.io/mithril/mithril.component.html#unloading-components
            $.each(filesWidgetCleanUp, function( index, value ) {
                m.mount(document.getElementById(value), null);
            });
            filesWidgetCleanUp = [];

            filePicker.destroy();
            filePicker = null;
        }
    }, null, 'beforeChange');


    var onSelectRow = function(item) {
        if (item.kind === 'file') {
            viewModel.addFile(item);
            item.css = 'fangorn-selected';
        }
    };
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
            dropzoneEvents: $.extend(
                {},
                Fangorn.DefaultOptions.dropzoneEvents,
                {
                    complete: function(tb, file, response) {
                        var fileResponse = JSON.parse(file.xhr.response);
                        var fileMeta = fileResponse.data.attributes;
                        fileMeta.nodeId = file.treebeardParent.data.nodeId;
                        onSelectRow({
                            kind: 'file',
                            data: fileMeta
                        });

                    }
                }
            ),
            onselectrow: onSelectRow,
            resolveRows: function(item) {
                var tb = this;

                item.css = '';

                limitContents(item);

                if (viewModel.value()) {
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
                if (tree.data.provider === 'osfstorage' && tree.data.nodeId === window.contextVars.node.id) {
                    this.multiselected([tree]);
                }

                tree.children.forEach(function(item) {
                    limitContents(item);

                    if (viewModel.value() !== null) {
                        if (item.data.path === viewModel.value()) {
                            item.css = 'fangorn-selected';
                            item.data.nodeId = tree.data.nodeId;
                            viewModel.addFile(item);
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
    fw.init().then(function() {
        viewModel.showUploader(false);
    });
    filesWidgetCleanUp.push(filePicker.fangornOpts.divID);
};

ko.bindingHandlers.osfUploader = {
    init: osfUploader
};


var uploaderCount = 0;
var Uploader = function(question, pk) {
    var self = this;

    self.draft_id = pk;
    question.showUploader = ko.observable(false);
    self.toggleUploader = function() {
        question.showUploader(!question.showUploader());
    };
    question.uid = 'uploader_' + uploaderCount;
    uploaderCount++;
    self.selectedFiles = ko.observableArray(question.extra() || []);
    self.selectedFiles.subscribe(function(fileList) {
        $.each(fileList, function(idx, file) {
            if (file && !self.fileAlreadySelected(file)) {
                question.extra().push(file);
            }
        });
        question.value(question.formattedFileList());
    });
    self.fileWarn = ko.observable(true);
    self.descriptionVisible = ko.pureComputed(function() {
        return (question.fileDescription ? question.fileDescription : false);
    }, self);
    self.value = ko.observable('');
    self.fileLimit = ko.pureComputed(function() {
        return (question.fileLimit ? question.fileLimit : 5);
    }, self);

    self.UPLOAD_LANGUAGE = 'You may attach up to ' + self.fileLimit() + ' file(s) to this question. You may attach files that you already have ' +
        'in this OSF project, or upload a new file from your computer. Uploaded files will automatically be added to this project ' +
        'so that they can be registered.';

    self.addFile = function(file) {
        self.value = ko.observable(file.data.descriptionvalue || '');
        if(self.selectedFiles().length >= self.fileLimit && self.fileWarn()) {
            self.fileWarn(false);
            bootbox.alert({
                title: 'Too many files',
                message: 'You cannot attach more than ' + self.fileLimit() + 'file(s) to a question.',
                buttons: {
                    ok: {
                        label: 'Close',
                        className: 'btn-default'
                    }
                }
            }).css({ 'top': '35%' });
            return false;
        } else if(self.selectedFiles().length >= self.fileLimit && !self.fileWarn()) {
            return false;
        }
        if(self.fileAlreadySelected(file))
            return false;

        var guid = self.getGuid(file).then(function (val) {
            self.setGuid(val, file.data.extra.hashes.sha256);
        });
        self.selectedFiles.push({
            fileId: guid,
            data: file.data,
            selectedFileName: file.data.name,
            nodeId: file.data.nodeId,
            viewUrl: '/project/' + file.data.nodeId + '/files/osfstorage' + file.data.path,
            sha256: file.data.extra.hashes.sha256,
            descriptionValue: self.value()
        });
        return true;
    };

    self.getGuid = function (file) {
        var ret = $.Deferred();
        var url = '/api/v1/project/' + file.data.nodeId + '/files/osfstorage' + file.data.path + '/?action=get_guid&draft=' + self.draft_id;
        var request = $osf.ajaxJSON('GET', url, {});

        request.done(function (resp) {
            ret.resolve(resp.guid);
        });

        return ret.promise();
    };

    self.setGuid = function (guid, sha256) {
        var files = question.extra();

        for (var i = 0; i < files.length; i++) {
            var file = files[i];
            if(file.sha256 === sha256) {
                self.selectedFiles()[i].fileId = guid;
                break;
            }
        }
    };

    self.fileAlreadySelected = function(file) {
        var selected = false;
        $.each(question.extra(), function(idx, alreadyFile) {
            if(alreadyFile.selectedFileName === file.data.name && alreadyFile.sha256 === file.data.extra.hashes.sha256){
                selected = true;
                return;
            }
        });
        return selected;
    };

    self.hasSelectedFile = ko.computed(function() {
        return question.extra().length !== 0;
    });
    self.unselectFile = function(fileToRemove) {

        var files = question.extra();

        for (var i = 0; i < files.length; i++) {
            var file = files[i];
            if(file.sha256 === fileToRemove.sha256) {
                self.selectedFiles.splice(i, 1);
                question.value(question.formattedFileList());
                break;
            }
        }
    };

    self.filePicker = null;

    self.preview = function() {
        var value = question.value();
        if (value === NO_FILE || question.extra().length === 0) {
            return 'no file selected';
        }
        else {
            var files = question.extra();
            var elem = '';
            $.each(files, function(_, file) {
                if (!file.data) { // old data may have empty file objects
                    return; // skip bad files
                }
                if(!file.data.descriptionValue){
                    elem += '<a target="_blank" href="' + file.viewUrl + '">' + $osf.htmlEscape(file.selectedFileName) + ' </a>' + '</br>';
                }else{
                    elem += '<span><a target="_blank" href="' + file.viewUrl + '">' + $osf.htmlEscape(file.selectedFileName) + ' </a>' + '  (' + file.data.descriptionValue + ')' + '</span></br>';
                }
            });
            return $(elem);
        }
    };

    $.extend(self, question);
};

var AuthorImport = function(data, $root, preview) {
    var self = this;
    self.question = data;

    /**
     * Makes ajax request for a project's contributors
     */
    self.makeContributorsRequest = function() {
        var contributorsUrl = window.contextVars.node.urls.api + 'get_contributors/';
        return $.getJSON(contributorsUrl);
    };
    /**
     * Returns the `user_fullname` of each contributor attached to a node.
     **/
    self.getContributors = function() {
        return self.makeContributorsRequest()
            .fail(function(xhr, status, error) {
                Raven.captureMessage('Could not GET contributors', {
                    extra: {
                        url: window.contextVars.node.urls.api + 'get_contributors/',
                        textStatus: status,
                        error: error
                    }
                });
                $osf.growl('Could not retrieve contributors.', osfLanguage.REFRESH_OR_SUPPORT);
            });
    };

    self.serializeContributors = function(contributors) {
        return $.map(contributors, function(c) {
            return c.fullname;
        }).join(', ');
    };
    self.makeContributorsRequest = function() {
        var self = this;
        var contributorsUrl = window.contextVars.node.urls.api + 'get_contributors/';
        return $.getJSON(contributorsUrl);
    };

    self.contributors = ko.observable([]);
    if (!preview) {
        self.getContributors().done(function(data) {
            self.question.value(self.serializeContributors(data.contributors));
        });
    }

    self.preview = function() {
        return $osf.htmlEscape(self.value());
    };
    var callback = function(data) {
        self.question.value(self.serializeContributors(data.contributors));
    };

    if ($('#addContributors').length > 0) {
        ko.cleanNode($('#addContributors')[0]);
        var adder = new ContribAdder(
            '#addContributors',
            node.title,
            node.id,
            null,
            null,
            {async: true, callback: callback}
        );
    }

    $.extend(self, data);
};

module.exports = {
    AuthorImport: AuthorImport,
    Uploader: Uploader,
    osfUploader: osfUploader,
    limitContents: limitContents
};

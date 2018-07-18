/**
 * Fangorn: Defining Treebeard options for OSF.
 * For Treebeard and _item API's check: https://github.com/caneruguz/treebeard/wiki
 */

'use strict';

var $ = require('jquery');
var m = require('mithril');
var URI = require('URIjs');
var Raven = require('raven-js');
var Treebeard = require('treebeard');
var moment = require('moment');
var Dropzone = require('dropzone');
var lodashGet = require('lodash.get');

var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');

var iconmap = require('js/iconmap');
var storageAddons = require('json-loader!storageAddons.json');

// CSS
require('css/fangorn.css');

var tbOptions;

var noop = function () { };

var tempCounter = 1;

var STATE_MAP = {
    upload: {
        display: 'Upload pending...'
    },
    copy: {
        display: 'Copying '
    },
    delete: {
        display: 'Deleting '
    },
    move: {
        display: 'Moving '
    },
    rename: {
        display: 'Renaming '
    }
};

var SYNC_UPLOAD_ADDONS = ['github', 'dataverse'];
var READ_ONLY_ADDONS = ['bitbucket', 'gitlab', 'onedrive'];

var CONFLICT_INFO = {
    skip: {
        passed: 'Skipped'
    },
    replace: {
        passed: 'Moved or replaced old version'
    },
    keep: {
        passed: 'Kept both versions'
    }
};

var OPERATIONS = {
    RENAME: {
        verb: 'Rename',
        status: 'rename',
        passed: 'renamed',
        action: 'Renaming'
    },
    MOVE: {
        verb: 'Move',
        status: 'move',
        passed: 'moved',
        action: 'Moving'
    },
    COPY: {
        verb: 'Copy',
        status: 'copy',
        passed: 'copied',
        action: 'Copying'
    }
};

// Cross browser key codes for the Command key
var COMMAND_KEYS = [224, 17, 91, 93];
var ESCAPE_KEY = 27;
var ENTER_KEY = 13;

function findByTempID(parent, tmpID) {
    var child;
    var item;
    for (var i = 0; i < parent.children.length; i++) {
        child = parent.children[i];
        if (!child.data.tmpID) {
            continue;
        }
        if (child.data.tmpID === tmpID) {
            item = child;
        }
    }
    return item;
}

var WIKI_IMAGES_FOLDER_PATH = '/Wiki images/';

/**
 * Cancel a pending upload
 * @this Treebeard.controller
 * @param {Object} row Treebeard row containing the file to cancel.
 */
function cancelUpload(row) {
    var tb = this;
    var cancelableStatuses = [Dropzone.UPLOADING, Dropzone.QUEUED];
    // Select files that are uploading, queued, or rejected (!accepted)
    var filesArr = tb.dropzone.files.filter(function(file) {
        return cancelableStatuses.indexOf(file.status) > -1 || !file.accepted;
    });
    var handled = false;
    // Search for and remove specified file from queue
    if (SYNC_UPLOAD_ADDONS.indexOf(row.data.provider) !== -1) {
        // Provider is handled in sync
        handled = tb.dropzone.syncFileCache[row.data.provider].some(function(file, index) {
            if (file.tmpID === row.data.tmpID) {
                tb.deleteNode(row.parentID, row.id);
                return tb.dropzone.syncFileCache[row.data.provider].splice(index, 1);
            }
        });
    }
    if (!handled) {
        // File is currently being uploaded/managed by dropzone
        handled = filesArr.some(function(file) {
            if (file.tmpID === row.data.tmpID) {
                tb.deleteNode(row.parentID, row.id);
                tb.dropzone.removeFile(file);
                return true;
            }
        });
    }
    tb.isUploading(handled && filesArr.length > 1);
}

/**
 * Cancel all pending uploads
 * @this Treebeard.controller
 */
function cancelAllUploads() {
    var tb = this;
    var cancelableStatuses = [Dropzone.UPLOADING, Dropzone.QUEUED];
    // Select files that are uploading, queued, or rejected (!accepted)
    var filesArr = tb.dropzone.files.filter(function(file) {
        return cancelableStatuses.indexOf(file.status) > -1 || !file.accepted;
    });
    // Remove all queued files
    var removeFromUI = function(file) {
        var parent = file.treebeardParent || tb.dropzoneItemCache;
        var item = findByTempID(parent, file.tmpID);
        tb.deleteNode(parent.id, item.id);
    };
    // Clear all synchronous uploads
    if (tb.dropzone.syncFileCache !== undefined) {
        SYNC_UPLOAD_ADDONS.forEach(function(provider) {
            if (tb.dropzone.syncFileCache[provider] !== undefined) {
                // Remove cached provider files from UI
                tb.dropzone.syncFileCache[provider].forEach(removeFromUI);
                // Clear provider cache
                tb.dropzone.syncFileCache[provider].length = 0;
            }
        });
    }
    // Clear all ongoing uploads
    filesArr.forEach(function(file, index) {
        // Ignore completed files
        if (file.upload.progress === 100) return;
        removeFromUI(file);
        // Cancel currently uploading file
        tb.dropzone.removeFile(file);
    });
    tb.isUploading(false);
}

var uploadRowTemplate = function(item) {
    var tb = this;
    var padding;
    if (tb.filterOn) {
        padding = 20;
    } else {
        padding = (item.depth - 1) * 20;
    }
    var columns = [{
        data : '',  // Data field name
        css : '',
        custom : function(){
            var uploadColumns = [
                m('.col-xs-7', {style: 'overflow: hidden;text-overflow: ellipsis;'}, [
                    m('span', { style : 'padding-left:' + padding + 'px;'}, tb.options.resolveIcon.call(tb, item)),
                    m('span', { style : 'margin-left: 9px;'}, item.data.name)
                ]),
                m('.col-xs-3',
                    m('.progress', [
                        m('.progress-bar.progress-bar-info.progress-bar-striped.active', {
                            role : 'progressbar',
                            'aria-valuenow' : item.data.progress,
                            'aria-valuemin' : '0',
                            'aria-valuemax': '100',
                            'style' : 'width: ' + item.data.progress + '%' }, m('span.sr-only', item.data.progress + '% Complete'))
                    ])
                )
            ];
            if (item.data.progress < 100) {
                uploadColumns.push(m('.col-xs-2', [
                    m('span', m('.fangorn-toolbar-icon.m-l-sm', {
                            style : 'padding: 0px 6px 2px 2px;font-size: 16px;display: inline;',
                            config : function() {
                                reapplyTooltips();
                            },
                            'onclick' : function (e) {
                                e.stopImmediatePropagation();
                                cancelUpload.call(tb, item);
                            }},
                         m('span.text-muted', '×')
                    ))
                ]));
            }
            return m('row.text-muted', uploadColumns);
        }
    }];
    if(tb.options.placement === 'files'){
        columns.push({
            data : '',  // Data field name
            custom : function(){ return '';}
        });
    }
    return columns;
};

/**
 * Returns custom icons for OSF depending on the type of item. Used for non-file icons.
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {Object}  Returns a mithril template with the m() function.
 */
function resolveIconView(item) {
    var icons = iconmap.projectComponentIcons;
    function returnView(type, category) {
        var iconType = icons[type];
        if(type === 'project' || type === 'component' || type === 'registeredProject' || type === 'registeredComponent') {
            if (item.data.permissions.view) {
                iconType = icons[category];
            } else {
                return null;
            }
        }
        if (type === 'registeredComponent' || type === 'registeredProject') {
            iconType += ' po-icon-registered';
        } else {
            iconType += ' po-icon';
        }
        var template = m('span', { 'class' : iconType});
        return template;
    }
    if (item.data.permissions){
        if (!item.data.permissions.view) {
            return m('span', { 'class' : iconmap.private });
        }
    }
    if (item.data.isDashboard) {
        return returnView('collection');
    }
    if (item.data.isSmartFolder) {
        return returnView('smartCollection');
    }
    if ((item.data.nodeType === 'pointer' && item.parent().data.nodeType !== 'folder') || (item.data.isPointer && !item.parent().data.isFolder)) {
        return returnView('link');
    }
    if (item.data.nodeType === 'project') {
        if (item.data.parentIsFolder && item.data.isFolder) {
            return returnView('collection');
        }
        if (item.data.isRegistration) {
            return returnView('registeredProject', item.data.category);
        } else {
            return returnView('project', item.data.category);
        }
    }
    if (item.data.nodeType === 'component') {
        if (item.data.isRegistration) {
            return returnView('registeredComponent', item.data.category);
        }
        return returnView('component', item.data.category);
    }

    if (item.data.nodeType === 'pointer') {
        return returnView('link');
    }
    return null;
}

/**
 * Returns custom icons for OSF depending on the type of item
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {Object}  Returns a mithril template with the m() function.
 * @private
 */
function _fangornResolveIcon(item) {
    if (item.data.unavailable)
        return m('div', {style: {width:'16px', height:'16px', background:'url(' + item.data.iconUrl+ ')', display:'inline-block', opacity: 0.4}}, '');

    var privateFolder = m('i.fa.fa-lock', ' '),
        pointerFolder = m('i.fa.fa-link', ' '),
        openFolder = m('i.fa.fa-folder-open', ' '),
        closedFolder = m('i.fa.fa-folder', ' '),
        configOption = item.data.provider ? resolveconfigOption.call(this, item, 'folderIcon', [item]) : undefined,  // jshint ignore:line
        icon;
    var newIcon = resolveIconView(item);
    if ( newIcon === null) {

        if (item.kind === 'folder') {
            if (item.data.iconUrl) {
                return m('div', {style: {width:'16px', height:'16px', background:'url(' + item.data.iconUrl+ ')', display:'inline-block'}}, '');
            }
            if (!item.data.permissions.view) {
                return privateFolder;
            }
            if (item.data.isPointer) {
                return pointerFolder;
            }
            if (item.open) {
                return configOption || openFolder;
            }
            return configOption || closedFolder;
        }
        if (item.data.icon) {
            return m('i.fa.' + item.data.icon, ' ');
        }
        return m('div.file-extension', { 'class': '_' + item.data.name.split('.').pop().toLowerCase() });
    }
    return newIcon;
}

// Addon config registry. this will be populated with add on specific items if any.
Fangorn.config = {};

/**
 * Returns add on specific configurations
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @param {String} key What the option is called in the add on object
 * @this Treebeard.controller
 * @returns {*} Returns the configuration, can be string, number, array, or function;
 */
function getconfig(item, key) {
    if (item && item.data.provider && Fangorn.config[item.data.provider]) {
        return Fangorn.config[item.data.provider][key];
    }
    return undefined;
}

/**
 * Gets a Fangorn config option if it is defined by an addon dev.
 * Calls it with `args` if it's a function otherwise returns the value.
 * If the config option is not defined, returns null
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @param {String} option What the option is called in the add on object
 * @param {Array} args An Array of whatever arguments will be sent with the .apply()
 * @this Treebeard.controller
 * @returns {*} Returns if its a property, runs the function if function, returns null if no option is defined.
 */
function resolveconfigOption(item, option, args) {
    var self = this,  // jshint ignore:line
        prop = getconfig(item, option);
    if (prop) {
        return typeof prop === 'function' ? prop.apply(self, args) : prop;
    }
    return null;
}

/**
 * Inherits a list of data fields from one item (parent) to another.
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @param {Object} parent A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 */
var inheritedFields = ['nodeId', 'nodeUrl', 'nodeApiUrl', 'permissions', 'provider', 'accept'];
function inheritFromParent(item, parent, fields) {
    inheritedFields.concat(fields || []).forEach(function(field) {
        item.data[field] = item.data[field] || parent.data[field];
    });

    if(item.data.provider === 'github' || item.data.provider === 'bitbucket' || item.data.provider === 'gitlab'){
        item.data.branch = parent.data.branch;
    }
}

/**
 * Returns custom folder toggle icons for OSF
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {string} Returns a mithril template with m() function, or empty string.
 * @private
 */
function _fangornResolveToggle(item) {
    var toggleMinus = m('i.fa.fa-minus', ' '),
        togglePlus = m('i.fa.fa-plus', ' '),
    // padding added so that this overlaps the toggle-icon div and prevent cursor change into pointer for checkout icons.
        checkedByUser = m('i.fa.fa-sign-out.text-muted[style="font-size: 120%; cursor: default; padding-top: 10px; padding-bottom: 10px; padding-right: 4px;"]', ''),
        checkedByOther = m('i.fa.fa-sign-out[style="color: #d9534f; font-size: 120%; cursor: default; padding-top: 10px; padding-bottom: 10px; padding-right: 4px;"]', '');
    // check if folder has children whether it's lazyloaded or not.
    if (item.kind === 'folder' && item.depth > 1) {
        if(!item.data.permissions.view){
            return '';
        }
        if (item.open) {
            return toggleMinus;
        }
        return togglePlus;
    }
    if (item.data.provider === 'osfstorage' && item.kind === 'file') {
        if (item.data.extra && item.data.extra.checkout) {
            if (item.data.extra.checkout._id === window.contextVars.currentUser.id){
                return checkedByUser;
            }
            return checkedByOther;
        }
    }
    return '';
}

/**
 * Checks if folder toggle is permitted (i.e. contents are private)
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {boolean}
 * @private
 */
function _fangornToggleCheck(item) {

    if (item.data.permissions.view) {
        return true;
    }
    item.notify.update('Not allowed: Private folder', 'warning', 1, undefined);
    return false;
}

function checkConflicts(items, folder){

    var children = {
      'names': [],
      'ids': []
    };
    var ret = {
        'conflicts' : [],
        'ready': []
    };

    folder.children.forEach(function(child){
        children.names.push(child.data.name);
        children.ids.push(child.id);
    });

    items.forEach(function(item) {
        if (children.names.includes(item.data.name) && !children.ids.includes(item.id)){
            ret.conflicts.push(item);
        } else {
            ret.ready.push(item);
        }
    });

    return ret;
}

function handleCancel(tb, provider, mode, item){
    if (mode === 'stop') {
        tb.syncFileMoveCache[provider].conflicts.length = 0;
        tb.modal.dismiss();
    } else {
        addFileStatus(tb, item, false, '', '', 'skip');
        doSyncMove(tb, provider);
    }
}

function displayConflict(tb, item, folder, cb) {

    if('/' + item.data.name + '/'  === WIKI_IMAGES_FOLDER_PATH) {
        $osf.growl('Error', 'You cannot replace the Wiki images folder');
        return;
    }

    var mithrilContent = m('', [
        m('p', 'An item named "' + item.data.name + '" already exists in this location.'),
        m('h5.replace-file',
            '"Keep Both" will retain both files (and their version histories) in this location.'),
        m('h5.replace-file',
            '"Replace" will overwrite the existing file in this location. ' +
            'You will lose previous versions of the overwritten file. ' +
            'You will keep previous versions of the moved file.'),
        m('h5.replace-file', '"Skip" will skip the current file.'),
        m('h5.replace-file', '"Stop" will only move files with no conflicts.')
    ]);
    var mithrilButtons = [
        m('span.btn.btn-primary.btn-sm', {onclick: cb.bind(tb, 'keep')}, 'Keep Both'),
        m('span.btn.btn-primary.btn-sm', {onclick: cb.bind(tb, 'replace')}, 'Replace'),
        m('span.btn.btn-default.btn-sm', {onclick: function() {handleCancel(tb, folder.data.provider, 'skip', item);}}, 'Skip'),
        m('span.btn.btn-danger.btn-sm', {onclick: function() {handleCancel(tb, folder.data.provider, 'stop');}}, 'Stop')
    ];
    var header = m('h3.break-word.modal-title', 'Replace "' + item.data.name + '"?');
    tb.modal.update(mithrilContent, mithrilButtons, header);
}

function checkConflictsRename(tb, item, name, cb) {
    var messageArray = [];
    var parent = item.parent();

    if(item.data.kind === 'folder' && parent.data.name === 'OSF Storage' && '/' + name + '/'  === WIKI_IMAGES_FOLDER_PATH){
        $osf.growl('Error', 'You cannot replace the Wiki images folder');
        return;
    }

    for(var i = 0; i < parent.children.length; i++) {
        var child = parent.children[i];
        if (child.data.name === name && child.id !== item.id) {
            messageArray.push([
                m('p', 'An item named "' + child.data.name + '" already exists in this location.'),
                m('h5.replace-file',
                    '"Keep Both" will retain both files (and their version histories) in this location.'),
                m('h5.replace-file',
                    '"Replace" will overwrite the existing file in this location. ' +
                    'You will lose previous versions of the overwritten file. ' +
                    'You will keep previous versions of the moved file.'),
                m('h5.replace-file', '"Cancel" will cancel the move.')
            ]);


            if (window.contextVars.node.preprintFileId === child.data.path.replace('/', '')) {
                messageArray = messageArray.concat([
                    m('p', 'The file "' + child.data.name + '" is the primary file for a preprint, so it should not be replaced.'),
                    m('strong', 'Replacing this file will remove this preprint from circulation.')
                ]);
            }
            tb.modal.update(
                m('', messageArray), [
                    m('span.btn.btn-default', {onclick: function() {tb.modal.dismiss();}}, 'Cancel'), //jshint ignore:line
                    m('span.btn.btn-primary', {onclick: cb.bind(tb, 'keep')}, 'Keep Both'),
                    m('span.btn.btn-primary', {onclick: cb.bind(tb, 'replace')}, 'Replace')
                ],
                m('h3.break-word.modal-title', 'Replace "' + child.data.name + '"?')
            );
            return;
        }
    }
    cb('replace');
}

function doItemOp(operation, to, from, rename, conflict) {
    var tb = this;
    // dismiss old modal immediately to prevent button mashing
    tb.modal.dismiss();
    var inReadyQueue;
    var filesRemaining;
    var inConflictsQueue = false;
    var syncMoves;

    var notRenameOp = typeof rename === 'undefined';
    if (notRenameOp) {
        filesRemaining = tb.syncFileMoveCache && tb.syncFileMoveCache[to.data.provider];
        syncMoves = SYNC_UPLOAD_ADDONS.indexOf(from.data.provider) !== -1;
        if (syncMoves) {
            inReadyQueue = filesRemaining && filesRemaining.ready && filesRemaining.ready.length > 0;
        }

        if (filesRemaining.conflicts) {
            inConflictsQueue = true;
            if (filesRemaining.conflicts.length > 0) {
                var s = filesRemaining.conflicts.length > 1 ? 's' : '';
                var mithrilContent = m('div', { className: 'text-center' }, [
                    m('p.h4', filesRemaining.conflicts.length + ' conflict' + s + ' left to resolve.'),
                    m('div', {className: 'ball-pulse ball-scale-blue text-center'}, [
                        m('div',''),
                        m('div',''),
                        m('div',''),
                    ])
                ]);
                var header =  m('h3.break-word.modal-title', operation.action + ' "' + from.data.name +'"');
                tb.modal.update(mithrilContent, m('', []), header);
            } else {
                // remove the empty queue to know there are no remaining conflicts next time
                filesRemaining.conflicts = undefined;
            }
        }
    }

    var ogParent = from.parentID;
    if (to.id === ogParent && (!rename || rename === from.data.name)){
        return;
    }

    if (operation === OPERATIONS.COPY) {
        from = tb.createItem($.extend(true, {status: operation.status}, from.data), to.id);
    } else {
        from.data.status = operation.status;
        from.move(to.id);
    }

    if (to.data.provider === from.provider) {
        tb.pendingFileOps.push(from.id);
    }
    orderFolder.call(tb, from.parent());

    var moveSpec;
    if (operation === OPERATIONS.RENAME) {
        moveSpec = {
            action: 'rename',
            rename: rename,
            conflict: conflict
        };
    } else if (operation === OPERATIONS.COPY) {
        moveSpec = {
            action: 'copy',
            path: to.data.path || '/',
            conflict: conflict,
            resource: to.data.nodeId,
            provider: to.data.provider
        };
    } else if (operation === OPERATIONS.MOVE) {
        moveSpec = {
            action: 'move',
            path: to.data.path || '/',
            conflict: conflict,
            resource: to.data.nodeId,
            provider: to.data.provider
        };
    }

    var options = {};
    if(from.data.provider === 'github' || from.data.provider === 'bitbucket' || from.data.provider === 'gitlab'){
        options.branch = from.data.branch;
        moveSpec.branch = from.data.branch;
    }

    from.inProgress = true;
    tb.clearMultiselect();

    $.ajax({
        type: 'POST',
        beforeSend: $osf.setXHRAuthorization,
        url: waterbutler.buildTreeBeardFileOp(from, options),
        contentType: 'application/json',
        data: JSON.stringify(moveSpec)
    }).done(function(resp, _, xhr) {
        if (to.data.provider === from.provider) {
            tb.pendingFileOps.pop();
        }
        if (xhr.status === 202) {
            var mithrilContent = m('div', [
                m('h3.break-word', operation.action + ' "' + (from.data.materialized || '/') + '" to "' + (to.data.materialized || '/') + '" is taking a bit longer than expected.'),
                m('p', 'We\'ll send you an email when it has finished.'),
                m('p', 'In the mean time you can leave this page; your ' + operation.status + ' will still be completed.')
            ]);
            var mithrilButtons = m('div', [
                m('span.tb-modal-btn', { 'class' : 'text-default', onclick : function() { tb.modal.dismiss(); }}, 'Close')
            ]);
            var header =  m('h3.modal-title.break-word', 'Operation Information');
            tb.modal.update(mithrilContent, mithrilButtons, header);
            return;
        }
        from.data = tb.options.lazyLoadPreprocess.call(this, resp).data;
        from.data.status = undefined;
        from.notify.update('Successfully ' + operation.passed + '.', 'success', null, 1000);

        if (xhr.status === 200) {
            to.children.forEach(function(child) {
                if (child.data.name === from.data.name && child.id !== from.id) {
                    child.removeSelf();
                }
            });
        }

        inheritFromParent(from, from.parent());

        if (from.data.kind === 'folder' && from.data.children) {
            from.children = [];
            var child;
            from.data.children.forEach(function(item) {
                child = tb.buildTree(item, from);
                inheritFromParent(child, from);
                from.add(child);
            });
            from.open = true;
            from.load = true;
        }
        var url = from.data.nodeUrl + 'files/' + from.data.provider + from.data.path;
        if (notRenameOp) {
            addFileStatus(tb, from, true, '', url, conflict);
        }
        // no need to redraw because fangornOrderFolder does it
        orderFolder.call(tb, from.parent());
    }).fail(function(xhr, textStatus) {
        if (to.data.provider === from.provider) {
            tb.pendingFileOps.pop();
        }
        if (operation === OPERATIONS.COPY) {
            from.removeSelf();
        } else {
            from.move(ogParent);
            from.data.status = undefined;
        }

        var message;

        if (xhr.status !== 500 && xhr.responseJSON && (xhr.responseJSON.message || xhr.responseJSON.message_long)) {
            message = xhr.responseJSON.message || xhr.responseJSON.message_long;
        } else if (xhr.status === 503) {
            message = textStatus;
        } else {
            message = 'Please refresh the page or contact ' + $osf.osfSupportLink() + ' if the problem persists.';
        }

        $osf.growl(operation.verb + ' failed.', message);

        Raven.captureMessage('Failed to move or copy file', {
            extra: {
                xhr: xhr,
                requestData: moveSpec
            }
        });
        if (notRenameOp) {
            addFileStatus(tb, from, false, '', '', conflict);
        }
        orderFolder.call(tb, from.parent());
    }).always(function(){
        from.inProgress = false;
        if (notRenameOp && (inConflictsQueue || syncMoves)) {
            doSyncMove(tb, to.data.provider);
        }
    });
}

/**
 * Find out what the upload URL is for each item
 * Because we use add ons each item will have something different. This needs to be in the json data.
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {String} Returns the url string from data or resolved through add on settings.
 * @private
 */
function _fangornResolveUploadUrl(item, file) {
    // WB v1 update syntax is PUT <file_path>?kind=file
    // WB v1 upload syntax is PUT <parent_path>/?kind=file&name=<filename>
    // If upload target file name already exists don't pass file.name.  WB v1 rejects updates that
    // include a filename.
    var configOption = resolveconfigOption.call(this, item, 'uploadUrl', [item, file]); // jshint ignore:line
    if (configOption) {
        return configOption;
    }
    var updateUrl;
    $.each(item.children, function( index, value ) {
        if (file.name === value.data.name) {
            updateUrl = waterbutler.buildTreeBeardUpload(value);
            return false;
        }
    });

    return updateUrl || waterbutler.buildTreeBeardUpload(item, {name: file.name});
}

/**
 * Event to fire when mouse is hovering over row. Currently used for hover effect.
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @param event The mouseover event from the browser
 * @this Treebeard.controller
 * @private
 */
function _fangornMouseOverRow(item, event) {
    $('.fg-hover-hide').hide();
    $(event.target).closest('.tb-row').find('.fg-hover-hide').show();
}

/**
 * Runs when dropzone uploadprogress is running, used for updating upload progress in view and models.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @param {Number} progress Progress number between 0 and 100
 * @this Dropzone
 * @private
 */
function _fangornUploadProgress(treebeard, file, progress) {
    var parent = file.treebeardParent;
    progress = Math.ceil(progress);
    for(var i = 0; i < parent.children.length; i++) {
        if (parent.children[i].data.tmpID !== file.tmpID) continue;
        if (parent.children[i].data.progress !== progress) {
            parent.children[i].data.progress = progress;
            m.redraw();
        }
        return;
    }
}

/**
 * Runs when dropzone sending method is running, used for updating the view while file is being sent.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @param xhr xhr information being sent
 * @param formData Dropzone's formdata information
 * @this Dropzone
 * @returns {*|null} Return isn't really used here by anything else.
 * @private
 */
function _fangornSending(treebeard, file, xhr, formData) {
    treebeard.options.uploadInProgress = true;
    var parent = file.treebeardParent || treebeard.dropzoneItemCache;
    xhr = $osf.setXHRAuthorization(xhr);
    var _send = xhr.send;
    xhr.send = function() {
        _send.call(xhr, file);
    };
    var configOption = resolveconfigOption.call(treebeard, parent, 'uploadSending', [file, xhr, formData]);
    return configOption || null;
}

/**
 * Runs when Dropzone's addedfile hook is run.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @this Dropzone
 * @returns {*|null}
 * @private
 */
function _fangornAddedFile(treebeard, file) {
    var item = file.treebeardParent;
    if (!_fangornCanDrop(treebeard, item)) {
        return;
    }

    if (SYNC_UPLOAD_ADDONS.indexOf(item.data.provider) !== -1) {
        this.syncFileCache = this.syncFileCache || {};
        this.syncFileCache[item.data.provider] = this.syncFileCache[item.data.provider] || [];

        var files = this.getActiveFiles().filter(function(f) {return f.isSync;});
        if (files.length > 0) {
            this.syncFileCache[item.data.provider].push(file);
            this.files.splice(this.files.indexOf(files), 1);
        }
        file.isSync = true;
    }

    var configOption = resolveconfigOption.call(treebeard, item, 'uploadAdd', [file, item]);

    var tmpID = tempCounter++;

    file.tmpID = tmpID;
    file.url = _fangornResolveUploadUrl(item, file);
    file.method = _fangornUploadMethod(item);

    var blankItem = {       // create a blank item that will refill when upload is finished.
        name: file.name,
        kind: 'file',
        provider: item.data.provider,
        children: [],
        permissions: {
            view: false,
            edit: false
        },
        tmpID: tmpID,
        progress: 0,
        uploadState : m.prop('uploading'),
    };
    var newitem = treebeard.createItem(blankItem, item.id);
    return configOption || null;
}

function _fangornCanDrop(treebeard, item) {
    var canDrop = resolveconfigOption.call(treebeard, item, 'canDrop', [item]);
    if (canDrop === null) {
        canDrop = item.data.provider && item.kind === 'folder' && item.data.permissions.edit;
    }
    return canDrop;
}

/**
 * Runs when Dropzone's dragover event hook is run.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param event DOM event object
 * @this Dropzone
 * @private
 */
function _fangornDragOver(treebeard, event) {
    var dropzoneHoverClass = 'fangorn-dz-hover',
        closestTarget = $(event.target).closest('.tb-row'),
        itemID = parseInt(closestTarget.attr('data-id')),
        item = treebeard.find(itemID);
    treebeard.select('.tb-row').removeClass(dropzoneHoverClass).removeClass(treebeard.options.hoverClass);
    if (item !== undefined) {
        if (_fangornCanDrop(treebeard, item)) {
            closestTarget.addClass(dropzoneHoverClass);
        }
    }
}

/**
 * Runs when Dropzone's drop event hook is run.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param event DOM event object
 * @this Dropzone
 * @private
 */
function _fangornDropzoneDrop(treebeard, event) {
    var dropzoneHoverClass = 'fangorn-dz-hover';
    treebeard.select('.tb-row').removeClass(dropzoneHoverClass);
}
/**
 * Runs when Dropzone's complete hook is run after upload is completed.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @this Dropzone
 * @private
 */
function _fangornComplete(treebeard, file) {
    var item = file.treebeardParent;
    resolveconfigOption.call(treebeard, item, 'onUploadComplete', [item]);
    orderFolder.call(treebeard, item);

    if (file.isSync) {
        if (this.syncFileCache[item.data.provider].length > 0) {
            var nextFile = this.syncFileCache[item.data.provider].pop();
            this.files.push(nextFile);
            this.processFile(nextFile);
        }
    }
}

/**
 * Runs when Dropzone's success hook is run.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @param {Object} response JSON response from the server
 * @this Dropzone
 * @private
 */
function _fangornDropzoneSuccess(treebeard, file, response) {
    treebeard.options.uploadInProgress = false;
    var parent = file.treebeardParent,
        item,
        revisedItem,
        child;
    for (var i = 0; i < parent.children.length; i++) {
        child = parent.children[i];
        if (!child.data.tmpID){
            continue;
        }
        if (child.data.tmpID === file.tmpID) {
            item = child;
        }
    }
    // RESPONSES
    // OSF : Object with actionTake : "file_added"
    // DROPBOX : Object; addon : 'dropbox'
    // S3 : Nothing
    // GITHUB : Object; addon : 'github'
    // Dataverse : Object, actionTaken : file_uploaded
    revisedItem = resolveconfigOption.call(treebeard, item.parent(), 'uploadSuccess', [file, item, response]);
    if (!revisedItem && response) {
        item.data = treebeard.options.lazyLoadPreprocess.call(this, response).data;
        inheritFromParent(item, item.parent());
    }
    if (item.data.tmpID) {
        item.data.tmpID = null;
        item.data.uploadState('completed');
    }
    // Remove duplicates if file was updated
    var status = file.xhr.status;
    if (status === 200) {
        parent.children.forEach(function(child) {
            if (child.data.name === item.data.name && child.id !== item.id) {
                child.removeSelf();
            }
        });
    }
    var url = item.data.nodeUrl + 'files/' + item.data.provider + item.data.path;
    addFileStatus(treebeard, file, true, '', url);

    if (item.data.provider === 'dataverse') {
        item.parent().data.datasetDraftModified = true;
    }

    treebeard.redraw();
}

function _fangornDropzoneRemovedFile(treebeard, file, message, xhr) {
    addFileStatus(treebeard, file, false, 'Upload Canceled.', '');
}
/**
 * runs when Dropzone's error hook runs. Notifies user with error.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @param message Error message returned
 * @private
 */
var DEFAULT_ERROR_MESSAGE = 'Could not upload file. The file may be invalid ' +
    'or the file folder has been deleted.';
function _fangornDropzoneError(treebeard, file, message, xhr) {
    var tb = treebeard;
    var msgText;

    // Unpatched Dropzone silently does nothing when folders are uploaded on Windows IE
    // Patched Dropzone.prototype.drop to emit error with file = 'None' to catch the error
    if (file === 'None'){
        $osf.growl('Error', 'Cannot upload folders.');
        return;
    }

    if (file.isDirectory) {
        msgText = 'Cannot upload folders.';
    } else if (xhr && xhr.status === 507) {
        msgText = 'Cannot upload file due to insufficient storage.';
    } else if (xhr && xhr.status === 0) {
        // There is no way for Safari to know if it was a folder at present
         msgText = '';
         if ($osf.isSafari()) {
             msgText += 'Could not upload file. Possible reasons: <br>';
             msgText += '1. Cannot upload folders. <br>2. ';
         }
         msgText += 'Unable to reach the provider, please try again later. ';
         msgText += 'If the problem persists, please contact ' + $osf.osfSupportEmail() + '.';
    } else {
        //Osfstorage and most providers store message in {Object}message.{string}message,
        //but some, like Dataverse, have it in {string} message.
        if (message){
            msgText = message.message ? message.message : (typeof message === 'string' ? message : DEFAULT_ERROR_MESSAGE);
        } else {
            msgText = DEFAULT_ERROR_MESSAGE;
        }
    }
    if (typeof file.isDirectory === 'undefined') {
        var parent = file.treebeardParent || treebeardParent.dropzoneItemCache; // jshint ignore:line
        var item;
        var child;
        var destroyItem = false;
        for (var i = 0; i < parent.children.length; i++) {
            child = parent.children[i];
            if (!child.data.tmpID) {
                continue;
            }
            if (child.data.tmpID === file.tmpID) {
                child.removeSelf();
            }
        }
    }
    console.error(file);
    treebeard.options.uploadInProgress = false;
    if (msgText !== 'Upload canceled.') {
        addFileStatus(treebeard, file, false, msgText, '');
    }
    treebeard.dropzone.options.queuecomplete(file);
}

/**
 * Click event for when upload buttonin Action Column, it essentially runs the hiddenFileInput.click
 * @param event DOM event object for click
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Information pertinent to that column where this upload event is run from
 * @private
 */
function _uploadEvent(event, item, col) {
    var self = this;  // jshint ignore:line
    try {
        event.stopPropagation();
    } catch (e) {
        window.event.cancelBubble = true;
    }
    self.dropzoneItemCache = item;
    self.dropzone.hiddenFileInput.click();
    if (!item.open) {
        self.updateFolder(null, item);
    }
}

/**
 * Download button in Action Column
 * @param event DOM event object for click
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Information pertinent to that column where this upload event is run from
 * @private
 */
function _downloadEvent (event, item, col) {
    try {
        event.stopPropagation();
    } catch (e) {
        window.event.cancelBubble = true;
    }
    window.location = waterbutler.buildTreeBeardDownload(item);
}

function _downloadZipEvent (event, item, col) {
    try {
        event.stopPropagation();
    } catch (e) {
        window.event.cancelBubble = true;
    }
    window.location = waterbutler.buildTreeBeardDownloadZip(item);
}

function _createFolder(event, dismissCallback, helpText) {
    var tb = this;
    helpText('');
    var val = $.trim(tb.select('#createFolderInput').val());
    var parent = tb.multiselected()[0];
    if (!parent.open) {
         tb.updateFolder(null, parent);
    }
    if (val.length < 1) {
        helpText('Please enter a folder name.');
        return;
    }
    if (val.indexOf('/') !== -1) {
        helpText('Folder name contains illegal characters.');
        return;
    }

    var extra = {};
    var path = parent.data.path || '/';
    var options = {name: val, kind: 'folder'};

    if ((parent.data.provider === 'github') || (parent.data.provider === 'gitlab')) {
        extra.branch = parent.data.branch;
        options.branch = parent.data.branch;
    }

    m.request({
        method: 'PUT',
        background: true,
        config: $osf.setXHRAuthorization,
        url: waterbutler.buildCreateFolderUrl(path, parent.data.provider, parent.data.nodeId, options, extra)
    }).then(function(item) {
        item = tb.options.lazyLoadPreprocess.call(this, item).data;
        inheritFromParent({data: item}, parent, ['branch']);
        item = tb.createItem(item, parent.id);
        orderFolder.call(tb, parent);
        item.notify.update('New folder created!', 'success', undefined, 1000);
        if(dismissCallback) {
            dismissCallback();
        }
    }, function(data) {
        if (data && data.code === 409) {
            helpText(data.message);
            m.redraw();
        } else {
            helpText('Folder creation failed.');
        }
    });
}
/**
 * Deletes the item, only appears for items
 * @param event DOM event object for click
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Information pertinent to that column where this upload event is run from
 * @private
 */

function _removeEvent (event, items, col) {
    var tb = this;
    function cancelDelete() {
        tb.modal.dismiss();
    }
    function runDelete(item) {
        tb.select('.modal-footer .btn-danger').html('<i> Deleting...</i>').removeClass('btn-danger').addClass('btn-default disabled');
        // delete from server, if successful delete from view
        var url = resolveconfigOption.call(this, item, 'resolveDeleteUrl', [item]);
        url = url || waterbutler.buildTreeBeardDelete(item);
        $.ajax({
            url: url,
            type: 'DELETE',
            beforeSend: $osf.setXHRAuthorization
        })
        .done(function(data) {
            // delete view
            tb.deleteNode(item.parentID, item.id);
            tb.modal.dismiss();
            tb.clearMultiselect();

            if (item.data.provider === 'dataverse') {
                item.parent().data.datasetDraftModified = true;
            }
        })
        .fail(function(data){
            tb.modal.dismiss();
            tb.clearMultiselect();
            if (data.responseJSON.message_long.indexOf('preprint') !== -1) {
                $osf.growl('Delete failed', data.responseJSON.message_long);
            }
            item.notify.update('Delete failed.', 'danger', undefined, 3000);
        });
    }
    function runDeleteMultiple(items){
        items.forEach(function(item){
            runDelete(item);
        });
    }

    function doDelete() {
        var folder = items[0];
        var deleteMessage;
        if (folder.data.permissions.edit) {
            if(folder.data.materialized === WIKI_IMAGES_FOLDER_PATH){
                deleteMessage = m('p.text-danger',
                    'This folder and all of its contents will be deleted. This folder is linked to ' +
                    'your wiki(s). Deleting it will remove images embedded in your wiki(s). ' +
                    'This action is irreversible.');
            } else {
                deleteMessage = m('p.text-danger',
                    'This folder and ALL its contents will be deleted. This action is irreversible.');
            }

            var mithrilContent = m('div', [deleteMessage]);
            var mithrilButtons = m('div', [
                m('span.btn.btn-default', { onclick : function() { cancelDelete.call(tb); } }, 'Cancel'),
                m('span.btn.btn-danger', { onclick : function() { runDelete(folder); } }, 'Delete')
            ]);
            tb.modal.update(mithrilContent, mithrilButtons, m('h3.break-word.modal-title', 'Delete "' + folder.data.name+ '"?'));
        } else {
            folder.notify.update('You don\'t have permission to delete this file.', 'info', undefined, 3000);
        }
    }

    // If there is only one item being deleted, don't complicate the issue:
    if(items.length === 1) {
        var detail;
        if(items[0].data.materialized.substring(0, WIKI_IMAGES_FOLDER_PATH.length) === WIKI_IMAGES_FOLDER_PATH) {
            detail = m('span', 'This file may be linked to your wiki(s). Deleting it will remove the' +
                ' image embedded in your wiki(s). ');
        } else {
            detail = '';
        }
        if(items[0].kind !== 'folder'){
            var mithrilContentSingle = m('div', [
                m('p.text-danger', detail, 'This action is irreversible.')
            ]);
            var mithrilButtonsSingle = m('div', [
                m('span.btn.btn-default', { onclick : function() { cancelDelete(); } }, 'Cancel'),
                m('span.btn.btn-danger', { onclick : function() { runDelete(items[0]); } }, 'Delete')
            ]);
            // This is already being checked before this step but will keep this edit permission check
            if(items[0].data.permissions.edit){
                tb.modal.update(mithrilContentSingle, mithrilButtonsSingle, m('h3.break-word.modal-title', 'Delete "' + items[0].data.name + '"?'));
            }
        }
        if(items[0].kind === 'folder') {
            if (!items[0].open) {
                tb.updateFolder(null, items[0], doDelete);
            } else {
                doDelete();
            }
        }
    } else {
        // Check if all items can be deleted
        var canDelete = true;
        var deleteList = [];
        var noDeleteList = [];
        var deleteMessage = [m('p', 'This action is irreversible.')];
        var mithrilContentMultiple;
        var mithrilButtonsMultiple;
        items.forEach(function(item, index, arr){
            if(!item.data.permissions.edit){
                canDelete = false;
                noDeleteList.push(item);
            } else {
                deleteList.push(item);
            }
            if(item.kind === 'folder' && deleteMessage.length === 1) {
                deleteMessage.push(m('p.text-danger', 'Some of the selected items are folders. This will delete the folder(s) and ALL of their content.'));
            }
        });
        // If all items can be deleted
        if(canDelete){
            mithrilContentMultiple = m('div', [
                    deleteMessage,
                    deleteList.map(function(n){
                        if(n.kind === 'folder'){
                            return m('.fangorn-canDelete.text-success.break-word', [
                                m('i.fa.fa-folder'), m('b', ' ' + n.data.name)
                                ]);
                        }
                        if(n.data.materialized.substring(0, WIKI_IMAGES_FOLDER_PATH.length) === WIKI_IMAGES_FOLDER_PATH) {
                            return m('p.text-danger', m('b', n.data.name), ' may be linked to' +
                                ' your wiki(s). Deleting them will remove images embedded in your wiki(s). ');
                        } else {
                            return m('.fangorn-canDelete.text-success.break-word', n.data.name);
                        }
                    })
                ]);
            mithrilButtonsMultiple = m('div', [
                    m('span.btn.btn-default', { onclick : function() { tb.modal.dismiss(); } }, 'Cancel'),
                    m('span.btn.btn-danger', { onclick : function() { runDeleteMultiple.call(tb, deleteList); } }, 'Delete All')
                ]);
        } else {
            mithrilContentMultiple = m('div', [
                    m('p', 'Some of these files can\'t be deleted but you can delete the ones highlighted with green. This action is irreversible.'),
                    deleteList.map(function(n){
                        if(n.kind === 'folder'){
                            return m('.fangorn-canDelete.text-success.break-word', [
                                m('i.fa.fa-folder'), m('b', ' ' + n.data.name)
                                ]);
                        }
                        return m('.fangorn-canDelete.text-success.break-word', n.data.name);
                    }),
                    noDeleteList.map(function(n){
                        return m('.fangorn-noDelete.text-warning.break-word', n.data.name);
                    })
                ]);
            mithrilButtonsMultiple = m('div', [
                    m('span.btn.btn-default', { 'class' : 'text-default', onclick : function() { tb.modal.dismiss(); } }, 'Cancel'),
                    m('span.btn.btn-danger', { 'class' : 'text-danger', onclick : function() { runDeleteMultiple.call(tb, deleteList); } }, 'Delete Some')
                ]);
        }
        tb.modal.update(mithrilContentMultiple, mithrilButtonsMultiple, m('h3.break-word.modal-title', 'Delete multiple files?'));
    }
}

function doCheckout(item, checkout, showError) {
    return $osf.ajaxJSON(
        'PUT',
        window.contextVars.apiV2Prefix + 'files' + item.data.path + '/',
        {
            isCors: true,
            data: {
                data: {
                    id: item.data.path.replace('/', ''),
                    type: 'files',
                    attributes: {
                        checkout: checkout
                    }
                }
            }
        }
    ).done(function(xhr) {
        if (showError) {
            window.location.reload();
        }
    }).fail(function(xhr) {
        if (showError) {
            $osf.growl('Error', 'Unable to check out file. This is most likely due to the file being already checked-out' +
                ' by another user.');
        }
    });
}


/**
 * Resolves lazy load url for fetching children
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {String|Boolean} Returns the fetch URL in string or false if there is no url.
 * @private
 */
function _fangornResolveLazyLoad(item) {
    item.connected = true;
    var configOption = resolveconfigOption.call(this, item, 'lazyload', [item]);
    if (configOption) {
        return configOption;
    }

    if (item.data.provider === undefined) {
        return false;
    }
    return waterbutler.buildTreeBeardMetadata(item);
}

/**
 * Handles errors in lazyload fetching of items, usually link is wrong
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _fangornLazyLoadError (item) {
    item.connected = false;
    var configOption = resolveconfigOption.call(this, item, 'lazyLoadError', [item]);
}

/**
 * Applies the positionining and initialization of tooltips for file names
 * @private
 */
function reapplyTooltips () {
    $('[data-toggle="tooltip"]').tooltip({container: 'body', 'animation' : false});
}

/**
 * Called when new object data has arrived to be loaded.
 * @param {Object} tree A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _fangornLazyLoadOnLoad (tree, event) {
    tree.children.forEach(function(item) {
        inheritFromParent(item, tree);
    });
    resolveconfigOption.call(this, tree, 'lazyLoadOnLoad', [tree, event]);
    reapplyTooltips();

    if (tree.depth > 1) {
        orderFolder.call(this, tree);
    }
}

/**
 * Order contents of a folder without an entire sorting of all the table
 * @param {Object} tree A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function orderFolder(tree) {
    var sortColumn;
    var sortDirection;

    if(typeof this.isSorted !== 'undefined' && typeof this.isSorted[0] !== 'undefined'){
        sortColumn = Object.keys(this.isSorted)[0]; // default to whatever column is first
        for (var column in this.isSorted){
            sortColumn = this.isSorted[column].asc || this.isSorted[column].desc ? column : sortColumn;
        }
        sortDirection = this.isSorted[sortColumn].desc ? 'desc' : 'asc'; // default to ascending
    }else{
        sortColumn = 0;
        sortDirection = 'asc';
    }
    tree.sortChildren(this, sortDirection, 'text', sortColumn, 1);
    this.redraw();
}

/**
 * Changes the upload method based on what the add ons need. Default is POST, S3 needs PUT
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {string} Must return string that is a legitimate method like POST, PUT
 * @private
 */
function _fangornUploadMethod(item) {
    var configOption = resolveconfigOption.call(this, item, 'uploadMethod', [item]);
    return configOption || 'PUT';
}

function gotoFileEvent (item, toUrl) {
    if(toUrl === undefined)
        toUrl = '/';
    var tb = this;
    var redir = new URI(item.data.nodeUrl);
    redir.segment('files').segment(item.data.provider).segmentCoded(item.data.path.substring(1));
    var fileurl  = redir.toString() + toUrl;

    // construct view only link into file url as it gets removed from url params in IE
    if ($osf.isIE()) {
        var viewOnly = $osf.urlParams().view_only;
        if (viewOnly) {
            if (fileurl.indexOf('?') !== -1) {
                fileurl += '&view_only=' + viewOnly;
            }else {
                fileurl += '?view_only=' + viewOnly;
            }
        }
    }

    if (COMMAND_KEYS.indexOf(tb.pressedKey) !== -1) {
        window.open(fileurl, '_blank');
    } else {
        window.open(fileurl, '_self');
    }
}

/**
 * Defines the contents of the title column (does not include the toggle and folder sections
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Options for this particulat column
 * @this Treebeard.controller
 * @returns {Array} Returns an array of mithril template objects using m()
 * @private
 */
function _fangornTitleColumnHelper(tb, item, col, nameTitle, toUrl, classNameOption){
    if (typeof tb.options.links === 'undefined') {
        tb.options.links = true;
    }
    // as opposed to undefined, avoids unnecessary setting of this value
    if (item.data.isAddonRoot && item.connected === false) {
        return _connectCheckTemplate.call(this, item);
    }
    if (item.kind === 'file' && item.data.permissions.view) {
        var attrs = {};
        if (tb.options.links) {
            attrs = {
                className: classNameOption,
                onclick: function(event) {
                    event.stopImmediatePropagation();
                    gotoFileEvent.call(tb, item, toUrl);
                }
            };
        }

        var titleRow = m('span', attrs, nameTitle);

        if  (item.data.extra.latestVersionSeen && item.data.extra.latestVersionSeen.seen === false && col.data === 'name') {
            titleRow = m('strong', [titleRow]);
        }

        return titleRow;
    }
    if ((item.data.nodeType === 'project' || item.data.nodeType ==='component') && item.data.permissions.view) {
        return m('a.' + classNameOption, {href: '/' + item.data.nodeID.toString() + toUrl}, nameTitle);
    }
    return m('span', nameTitle);
}

function _fangornTitleColumn(item, col) {
    var tb = this;
    if(item.data.nodeRegion){
        return _fangornTitleColumnHelper(tb, item, col, item.data.name + ' (' + item.data.nodeRegion + ')', '/', 'fg-file-links');
    }
    return _fangornTitleColumnHelper(tb, item, col, item.data.name, '/', 'fg-file-links');
}

function _fangornVersionColumn(item, col) {
    var tb = this;
    if (item.kind !== 'folder' && item.data.provider === 'osfstorage'){
        return _fangornTitleColumnHelper(tb, item, col, String(item.data.extra.version), '/?show=revision', 'fg-version-links');
    }
    return;
}

/**
 * Defines the contents of the modified column (does not include the toggle and folder sections
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Options for this particular column
 * @this Treebeard.controller
 * @returns {Array} Returns an array of mithril template objects using m()
 * @private
 */
function _fangornModifiedColumn(item, col) {
    var tb = this;
    if (item.data.isAddonRoot && item.connected === false) { // as opposed to undefined, avoids unnecessary setting of this value
        return _connectCheckTemplate.call(this, item);
    }
    if (item.kind === 'file' && item.data.permissions.view && item.data.modified_utc) {
        item.data.modified = new moment(moment.utc(item.data.modified_utc,'YYYY-MM-DD hh:mm A', 'en').toDate()).format('YYYY-MM-DD hh:mm A');
        return m(
            'span',
            item.data.modified
        );
    }
    return m('span', '');
}

/**
 * Returns a reusable template for column titles when there is no connection
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _connectCheckTemplate(item){
    var tb = this;
    return m('span.text-danger', [
        m('span', item.data.name),
        m('em', ' couldn\'t load.' ),
        m('button.btn.btn-xs.btn-default.m-l-xs', {
            onclick : function(e){
                e.stopImmediatePropagation();
                if (tb.options.togglecheck.call(tb, item)) {
                    var index = tb.returnIndex(item.id);
                    tb.toggleFolder(index, e);
                }
            }
        }, [m('i.fa.fa-refresh'), ' Retry'])
    ]);
}

/**
 * Parent function for resolving rows, all columns are sub methods within this function
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {Array} An array of columns that get iterated through in Treebeard
 * @private
 */
function _fangornResolveRows(item) {
    var tb = this;
    var defaultColumns = [];
    var configOption;
    item.css = '';
    if(tb.isMultiselected(item.id)){
        item.css = 'fangorn-selected';
    }

    if(item.data.permissions && !item.data.permissions.view){
        item.css += ' tb-private-row';
    }

    if(item.data.uploadState && (item.data.uploadState() === 'pending' || item.data.uploadState() === 'uploading')){
        return uploadRowTemplate.call(tb, item);
    }

    if (item.data.status) {
        return [{
            data : '',  // Data field name
            css : 't-a-c',
            custom : function(){ return m('span.text-muted', [STATE_MAP[item.data.status].display, item.data.name, '...']); }
        }, {
            data : '',  // Data field name
            custom : function(){ return '';}
        }];
    }
    if (item.parentID) {
        item.data.permissions = item.data.permissions || item.parent().data.permissions;
        if (item.data.kind === 'folder') {
            item.data.accept = item.data.accept || item.parent().data.accept;
        }
    }
    defaultColumns.push({
        data : 'name',  // Data field name
        folderIcons : true,
        filter : true,
        custom : _fangornTitleColumn
    });
    defaultColumns.push({
        data : 'size',  // Data field name
        sortInclude : false,
        filter : false,
        custom : function() {return item.data.size ? $osf.humanFileSize(item.data.size, true) : '';}
    });
    defaultColumns.push({
        data: 'version',
        filter: false,
        sortInclude : false,
        custom: _fangornVersionColumn
    });
    if (item.data.provider === 'osfstorage') {
        defaultColumns.push({
            data : 'downloads',
            sortInclude : false,
            filter : false,
            custom: function() { return lodashGet(item, 'data.extra.downloads', '').toString(); }
        });
    } else {
        defaultColumns.push({
            data : 'downloads',
            sortInclude : false,
            filter : false,
            custom : function() { return m(''); }
        });
    }
    defaultColumns.push({
        data : 'modified',  // Data field name
        filter : false,
        custom : _fangornModifiedColumn
    });
    configOption = resolveconfigOption.call(this, item, 'resolveRows', [item]);
    return configOption || defaultColumns;
}

/**
 * Defines Column Titles separately since content and css may be different, allows more flexibility
 * @returns {Array} an Array of column information that gets templated inside Treebeard
 * @this Treebeard.controller
 * @private
 */
function _fangornColumnTitles () {
    var columns = [];
    columns.push({
        title : 'Name',
        width : '54%',
        sort : true,
        sortType : 'text'
    }, {
        title : 'Size',
        width : '8%',
        sort : false
    }, {
        title : 'Version',
        width : '10%',
        sort : false
    }, {
        title : 'Downloads',
        width : '8%',
        sort : false
    }, {
        title : 'Modified',
        width : '20%',
        sort : true,
        sortType : 'text'
    });
    return columns;
}

/**
 * When fangorn loads the top level needs to be open so we load the children on load
 * @this Treebeard.controller
 * @private
 */
function _loadTopLevelChildren() {
    var i;
    for (i = 0; i < this.treeData.children.length; i++) {
        this.updateFolder(null, this.treeData.children[i]);
    }
}

/**
 * Expand major addons on load
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
var NO_AUTO_EXPAND_PROJECTS = ['ezcuj', 'ecmz4', 'w4wvg', 'sn64d'];
function expandStateLoad(item) {
    var tb = this,
        icon = $('.tb-row[data-id="' + item.id + '"]').find('.tb-toggle-icon'),
        toggleIcon = tbOptions.resolveToggle(item),
        addonList = [],
        i;

    if (item.children.length > 0 && item.depth === 1) {
        // NOTE: On the RPP and a few select projects *only*: Load the top-level project's OSF Storage
        // but do NOT lazy-load children in order to save hundreds of requests.
        // TODO: We might want to do this for every project, but that's TBD.
        // /sloria
        if (window.contextVars && window.contextVars.node && NO_AUTO_EXPAND_PROJECTS.indexOf(window.contextVars.node.id) > -1) {
            var osfsItems = item.children.filter(function(child) { return child.data.isAddonRoot && child.data.provider === 'osfstorage'; });
            if (osfsItems.length) {
                var osfsItem = osfsItems[0];
                tb.updateFolder(null, osfsItem);
            }
        } else {
            for (i = 0; i < item.children.length; i++) {
                tb.updateFolder(null, item.children[i]);
            }
        }
    }

    if (item.children.length > 0 && item.depth === 2) {
        for (i = 0; i < item.children.length; i++) {
            if (item.children[i].data.isAddonRoot || item.children[i].data.addonFullName === 'OSF Storage' ) {
                tb.updateFolder(null, item.children[i]);
            }
        }
    }

    if (item.depth > 2 && !item.data.isAddonRoot && !item.data.type && item.children.length === 0 && item.open) {
        // Displays loading indicator until request below completes
        // Copied from toggleFolder() in Treebeard
        if (icon.get(0)) {
            m.render(icon.get(0), tbOptions.resolveRefreshIcon());
        }
        $osf.ajaxJSON(
            'GET',
            '/api/v1/project/' + item.data.nodeID + '/files/grid/'
        ).done(function(response) {
            var data = response.data[0].children;
            tb.updateFolder(data, item);
            tb.redraw();
        }).fail(function(xhr) {
            item.notify.update('Unable to retrieve components.', 'danger', undefined, 3000);
            item.open = false;
            Raven.captureMessage('Unable to retrieve components for node ' + item.data.nodeID, {
                extra: {
                    xhr: xhr
                }
            });
        });
    }

    $('.fangorn-toolbar-icon').tooltip();

}

/**
 * @param tree A Treebeard _item object for the row
 * @param nodeID Current node._id
 * @param file window.contextVars.file object
 */
function setCurrentFileID(tree, nodeID, file) {
    var tb = this;
    if(!file){
        return;
    }
    var child;
    var i;
    if (file.provider === 'figshare') {
        for (i = 0; i < tree.children.length; i++) {
            child = tree.children[i];
            if (nodeID === child.data.nodeId && child.data.provider === file.provider && child.data.path === file.path) {
                tb.currentFileID = child.id;
            }
        }
    } else if (file.provider === 'dataverse') {
        // Only highlight file in correct dataset version, since paths persist across versions
        for (i = 0; i < tree.children.length; i++) {
            child = tree.children[i];
            var urlParams = $osf.urlParams();
            if (nodeID === child.data.nodeId && child.data.provider === file.provider && child.data.path === file.path &&
                child.data.extra.datasetVersion === urlParams.version) {
                tb.currentFileID = child.id;
            }
        }
    } else if (tb.fangornFolderIndex !== undefined && tb.fangornFolderArray !== undefined && tb.fangornFolderIndex < tb.fangornFolderArray.length) {
        for (var j = 0; j < tree.children.length; j++) {
            child = tree.children[j];
            if (nodeID === child.data.nodeId && child.data.provider === file.provider && child.data.name === tb.fangornFolderArray[tb.fangornFolderIndex]) {
                tb.fangornFolderIndex++;
                if (child.data.kind === 'folder') {
                    tb.updateFolder(null, child);
                    tree = child;
                }
                else {
                    tb.currentFileID = child.id;
                }
            }
        }
    }
}

/**
 * Scroll to the Treebeard item corresponding to the given ID
 * @param fileID id of a Treebeard _item object
 */
function scrollToFile(fileID) {
    var tb = this;
    if (fileID !== undefined) {
        var index = tb.returnIndex(fileID);
        var visibleIndex = tb.visibleIndexes.indexOf(index);
        var scrollTo = visibleIndex * tb.options.rowHeight;
        this.select('#tb-tbody').scrollTop(scrollTo);
    }
}

function _renameEvent () {
    var tb = this;
    var item = tb.multiselected()[0];
    var val = $.trim($('#renameInput').val());
    var folder = item.parent();
    //TODO Error message?
    if  (val === item.name) {
        return;
    }
    if(item.data.materialized === WIKI_IMAGES_FOLDER_PATH){
        $osf.growl('Error', 'You cannot rename your Wiki images folder.');
        return;
    }

    checkConflictsRename(tb, item, val, doItemOp.bind(tb, OPERATIONS.RENAME, folder, item, val));
    tb.toolbarMode(toolbarModes.DEFAULT);
}

var toolbarModes = {
    'DEFAULT' : 'bar',
    'FILTER' : 'filter',
    'ADDFOLDER' : 'addFolder',
    'RENAME' : 'rename',
    'ADDPROJECT' : 'addProject'
};


// A fangorn-styled button; addons can reuse this
var FGButton = {
    view: function(ctrl, args, children) {
        var extraCSS = args.className || '';
        var tooltipText = args.tooltip || '';
        var iconCSS = args.icon || '';
        var onclick = args.onclick || noop;
        var opts = {
            className: 'fangorn-toolbar-icon ' + extraCSS,
            onclick: onclick
        };
        // Add tooltip if applicable
        if (args.tooltip) {
            opts['data-toggle'] = 'tooltip';
            opts['data-placement'] = 'bottom';
            opts.title = args.tooltip;
        }
        var childrenElements = [];
        childrenElements.push(m('i', {className: iconCSS}));
        if(children) {
            childrenElements.push(m('span', children));
        }
        return m('div', opts, childrenElements);
    }
};

var FGInput = {
    view : function(ctrl, args, helpText) {
        var extraCSS = args.className || '';
        var tooltipText = args.tooltip || '';
        var placeholder = args.placeholder || '';
        var id = args.id || '';
        var helpTextId = args.helpTextId || '';
        var oninput = args.oninput || noop;
        var onkeypress = args.onkeypress || noop;
        return m('span', [
            m('input', {
                'id' : id,
                className: 'pull-right form-control' + extraCSS,
                oninput: oninput,
                onkeypress: onkeypress,
                'value': args.value || '',
                'data-toggle': tooltipText ? 'tooltip' : '',
                'title': tooltipText,
                'data-placement' : 'bottom',
                'placeholder' : placeholder
                }),
            m('.text-danger', {
                'id' : helpTextId
            }, helpText)
        ]);
    }
};

var FGDropdown = {
    view : function(ctrl, args, children) {
        var extraCSS = args.className || '';
        var tooltipText = args.tooltip || '';
        var id = args.id || '';
        var name = args.name || '';
        var label = args.label || '';
        var onchange = args.onchange || noop;
        return m('span.fangorn-dropdown', {
                className: extraCSS
            }, [
                m('span.hidden-xs', label),
                m('select.no-border', {
                    'name' : name,
                    'id' : id,
                    onchange: onchange,
                    'data-toggle': tooltipText ? 'tooltip' : '',
                    'title': tooltipText,
                    'data-placement' : 'bottom'
                }, children)
        ]);
    }
};

var FGItemButtons = {
    view : function(ctrl, args, children) {
        var tb = args.treebeard;
        var item = args.item;
        var rowButtons = [];
        var mode = args.mode;
        var preprintPath = getPreprintPath(window.contextVars.node.preprintFileId);
        if (tb.options.placement !== 'fileview') {
            if (window.File && window.FileReader && item.kind === 'folder' && item.data.provider && item.data.permissions && item.data.permissions.edit) {
                rowButtons.push(
                    m.component(FGButton, {
                        onclick: function(event) {_uploadEvent.call(tb, event, item); },
                        icon: 'fa fa-upload',
                        className : 'text-success'
                    }, 'Upload'),
                    m.component(FGButton, {
                        onclick: function () {
                            mode(toolbarModes.ADDFOLDER);
                        },
                        icon: 'fa fa-plus',
                        className: 'text-success'
                    }, 'Create Folder'));
                if (item.data.path) {
                    if (preprintPath && folderContainsPreprint(item, preprintPath)) {
                        rowButtons.push(
                            m.component(FGButton, {
                                icon: 'fa fa-trash',
                                tooltip: 'This folder contains a Preprint. You cannot delete Preprints, but you can upload a new version.',
                                className: 'tb-disabled'
                            }, 'Delete Folder'));
                        reapplyTooltips();
                    } else {
                        rowButtons.push(
                            m.component(FGButton, {
                                onclick: function(event) {_removeEvent.call(tb, event, [item]); },
                                icon: 'fa fa-trash',
                                className : 'text-danger'
                            }, 'Delete Folder'));
                    }
                }
            }
            if (item.kind === 'file') {
                rowButtons.push(
                    m.component(FGButton, {
                        onclick: function (event) { _downloadEvent.call(tb, event, item); },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download')
                );
                if (item.data.permissions && item.data.permissions.view) {
                    rowButtons.push(
                        m.component(FGButton, {
                            onclick: function (event) {
                                gotoFileEvent.call(tb, item, '/');
                            },
                            icon: 'fa fa-file-o',
                            className: 'text-info'
                        }, 'View'));
                }
                if (item.data.permissions && item.data.permissions.edit) {
                    if (item.data.provider === 'osfstorage') {
                        if (!item.data.extra.checkout){
                            if (preprintPath && preprintPath === item.data.path) {
                                // Block delete for preprint files
                                rowButtons.push(
                                    m.component(FGButton, {
                                        icon: 'fa fa-trash',
                                        tooltip: 'This file is a Preprint. You cannot delete Preprints, but you can upload a new version.',
                                        className: 'tb-disabled'
                                    }, 'Delete'));
                                // Tooltips don't seem to auto reapply, this forces them.
                                reapplyTooltips();
                            } else {
                                rowButtons.push(
                                    m.component(FGButton, {
                                        onclick: function(event) { _removeEvent.call(tb, event, [item]); },
                                        icon: 'fa fa-trash',
                                        className: 'text-danger'
                                    }, 'Delete'));
                            }
                            rowButtons.push(
                                m.component(FGButton, {
                                    onclick: function(event) {
                                        tb.modal.update(m('', [
                                            m('p', 'This would mean ' +
                                                'other contributors cannot edit, delete or upload new versions of this file ' +
                                                'as long as it is checked-out. You can check it back in at anytime.')
                                        ]), m('', [
                                            m('a.btn.btn-default', {onclick: function() {tb.modal.dismiss();}}, 'Cancel'), //jshint ignore:line
                                            m('a.btn.btn-warning', {onclick: function() {
                                                doCheckout(item, window.contextVars.currentUser.id, true);
                                            }}, 'Check out file')
                                        ]), m('h3.break-word.modal-title', 'Confirm file check-out?'));
                                    },
                                    icon: 'fa fa-sign-out',
                                    className : 'text-warning'
                                }, 'Check out file'));
                        } else if (item.data.extra.checkout && item.data.extra.checkout._id === window.contextVars.currentUser.id) {
                            rowButtons.push(
                                m.component(FGButton, {
                                    onclick: function(event) {
                                        doCheckout(item, null, true);
                                    },
                                    icon: 'fa fa-sign-in',
                                    className : 'text-warning'
                                }, 'Check in file')
                            );
                        }
                    } else {
                        rowButtons.push(
                        m.component(FGButton, {
                            onclick: function (event) { _removeEvent.call(tb, event, [item]); },
                            icon: 'fa fa-trash',
                            className: 'text-danger'
                        }, 'Delete'));

                    }
                }
                if(storageAddons[item.data.provider].externalView) {
                    var providerFullName = storageAddons[item.data.provider].fullName;
                    rowButtons.push(
                        m('a.text-info.fangorn-toolbar-icon', {href: item.data.extra.webView}, [
                            m('i.fa.fa-external-link'),
                            m('span', 'View on ' + providerFullName)
                        ])
                    );
                }
            } else if (item.data.provider) {
                rowButtons.push(
                    m.component(FGButton, {
                        onclick: function (event) { _downloadZipEvent.call(tb, event, item); },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download as zip')
                );
            }
            if (item.data.provider && !item.data.isAddonRoot && item.data.permissions && item.data.permissions.edit && (item.data.provider !== 'osfstorage' || !item.data.extra.checkout)) {
                rowButtons.push(
                    m.component(FGButton, {
                        onclick: function () {
                            mode(toolbarModes.RENAME);
                        },
                        icon: 'fa fa-pencil',
                        className: 'text-info'
                    }, 'Rename')
                );
            }
            return m('span', rowButtons);
        }
    }
};

var dismissToolbar = function(helpText){
    var tb = this;
    if (tb.toolbarMode() === toolbarModes.FILTER){
        tb.resetFilter();
    }
    tb.toolbarMode(toolbarModes.DEFAULT);
    tb.filterText('');
    if(typeof helpText === 'function'){
        helpText('');
    }
    m.redraw();
};

var FGToolbar = {
    controller : function(args) {
        var self = this;
        self.tb = args.treebeard;
        self.tb.toolbarMode = m.prop(toolbarModes.DEFAULT);
        self.items = args.treebeard.multiselected;
        self.mode = self.tb.toolbarMode;
        self.isUploading = args.treebeard.isUploading;
        self.helpText = m.prop('');
        self.dismissToolbar = dismissToolbar.bind(self.tb, self.helpText);
        self.createFolder = function(event){
            _createFolder.call(self.tb, event, self.dismissToolbar, self.helpText);
        };
        self.nameData = m.prop('');
        self.renameId = m.prop('');
        self.renameData = m.prop('');
    },
    view : function(ctrl) {
        var templates = {};
        var generalButtons = [];
        var finalRowButtons = [];
        var items = ctrl.items();
        var item = items[0];
        var dismissIcon = m.component(FGButton, {
                onclick: ctrl.dismissToolbar,
                icon : 'fa fa-times'
            }, '');
        templates[toolbarModes.FILTER] = [
            m('.col-xs-9', [
                ctrl.tb.options.filterTemplate.call(ctrl.tb)
                ]),
                m('.col-xs-3.tb-buttons-col',
                    m('.fangorn-toolbar.pull-right', [dismissIcon])
                )
            ];
        $('.tb-row').click(function(){
            ctrl.helpText('');
        });

        if (ctrl.tb.toolbarMode() === toolbarModes.DEFAULT) {
            ctrl.nameData('');
            ctrl.renameId('');
        }
        if(typeof item !== 'undefined' && item.id !== ctrl.renameId()){
            ctrl.renameData(item.data.name);
            ctrl.renameId(item.id);
        }

        if (ctrl.tb.options.placement !== 'fileview') {
            templates[toolbarModes.ADDFOLDER] = [
                m('.col-xs-9', [
                    m.component(FGInput, {
                        oninput: m.withAttr('value', ctrl.nameData),
                        onkeypress: function (event) {
                            if (ctrl.tb.pressedKey === ENTER_KEY) {
                                ctrl.createFolder.call(ctrl.tb, event, ctrl.dismissToolbar);
                            }
                        },
                        id: 'createFolderInput',
                        value: ctrl.nameData(),
                        helpTextId: 'createFolderHelp',
                        placeholder: 'New folder name',
                    }, ctrl.helpText())
                ]),
                m('.col-xs-3.tb-buttons-col',
                    m('.fangorn-toolbar.pull-right',
                        [
                            m.component(FGButton, {
                                onclick: ctrl.createFolder,
                                icon: 'fa fa-plus',
                                className: 'text-success'
                            }),
                            dismissIcon
                        ]
                    )
                )
            ];
            templates[toolbarModes.RENAME] = [
                m('.col-xs-9',
                    m.component(FGInput, {
                        oninput: m.withAttr('value', ctrl.renameData),
                        onkeypress: function (event) {
                            if (ctrl.tb.pressedKey === ENTER_KEY) {
                                _renameEvent.call(ctrl.tb);
                            }
                        },
                        id: 'renameInput',
                        value: ctrl.renameData(),
                        helpTextId: 'renameHelpText',
                        placeholder: 'Enter name',
                    }, ctrl.helpText())
                ),
                m('.col-xs-3.tb-buttons-col',
                    m('.fangorn-toolbar.pull-right',
                        [
                            m.component(FGButton, {
                                onclick: function () {
                                    _renameEvent.call(ctrl.tb);
                                },
                                icon: 'fa fa-pencil',
                                className: 'text-info'
                            }),
                            dismissIcon
                        ]
                    )
                )
            ];
        }
        // Bar mode
        // Which buttons should show?
        if(items.length === 1){
            var addonButtons = resolveconfigOption.call(ctrl.tb, item, 'itemButtons', [item]);
            if (addonButtons) {
                finalRowButtons = m.component(addonButtons, {treebeard : ctrl.tb, item : item }); // jshint ignore:line
            } else if (ctrl.tb.options.placement !== 'fileview') {
                finalRowButtons = m.component(FGItemButtons, {treebeard : ctrl.tb, mode : ctrl.mode, item : item }); // jshint ignore:line
            }
        }
        if(ctrl.isUploading() && ctrl.tb.options.placement !== 'fileview') {
            generalButtons.push(
                m.component(FGButton, {
                    onclick: function() {
                        cancelAllUploads.call(ctrl.tb);
                    },
                    icon: 'fa fa-time-circle',
                    className : 'text-danger'
                }, 'Cancel Pending Uploads')
            );
        }
        // multiple selection icons
        // Special cased to not show 'delete multiple' for github or published dataverses
        if(
            (items.length > 1) &&
            (ctrl.tb.multiselected()[0].data.provider !== 'github') &&
            (ctrl.tb.multiselected()[0].data.provider !== 'onedrive') &&
            (ctrl.tb.options.placement !== 'fileview') &&
            !(
                (ctrl.tb.multiselected()[0].data.provider === 'dataverse') &&
                (ctrl.tb.multiselected()[0].parent().data.version === 'latest-published')
            )
        ) {
            if (showDeleteMultiple(items)) {
                var preprintPath = getPreprintPath(window.contextVars.node.preprintFileId);
                if (preprintPath && multiselectContainsPreprint(items, preprintPath)) {
                    generalButtons.push(
                        m.component(FGButton, {
                            icon: 'fa fa-trash',
                            tooltip: 'One of these items is a Preprint or contains a Preprint. You cannot delete Preprints, but you can upload a new version.',
                            className: 'tb-disabled'
                        }, 'Delete Multiple')
                    );
                } else {
                    generalButtons.push(
                        m.component(FGButton, {
                            onclick: function(event) {
                                var configOption = resolveconfigOption.call(ctrl.tb, item, 'removeEvent', [event, items]); // jshint ignore:line
                                if(!configOption){ _removeEvent.call(ctrl.tb, null, items); }
                            },
                            icon: 'fa fa-trash',
                            className : 'text-danger'
                        }, 'Delete Multiple')
                    );
                }
            }
        }
        generalButtons.push(
            m.component(FGButton, {
                onclick: function(event){
                    ctrl.mode(toolbarModes.FILTER);
                },
                icon: 'fa fa-search',
                className : 'text-primary'
            }, 'Filter'));
            if (ctrl.tb.options.placement !== 'fileview') {
                generalButtons.push(m.component(FGButton, {
                    onclick: function(event){
                        var mithrilContent = m('div', [
                            m('p', [ m('b', 'Select rows:'), m('span', ' Click on a row (outside the add-on, file, or folder name) to show further actions in the toolbar. Use Command or Shift keys to select multiple files.')]),
                            m('p', [ m('b', 'Open files:'), m('span', ' Click a file name to go to view the file in the OSF.')]),
                            m('p', [ m('b', 'Open files in new tab:'), m('span', ' Press Command (Ctrl in Windows) and click a file name to open it in a new tab.')]),
                            m('p', [ m('b', 'Download as zip:'), m('span', ' Click on the row of an add-on or folder and click the Download as Zip button in the toolbar.'), m('i', ' Not available for all storage add-ons.')]),
                            m('p', [ m('b', 'Copy files:'), m('span', ' Press Option (Alt in Windows) while dragging a file to a new folder or component.'), m('i', ' Only for contributors with write access.')])
                        ]);
                        var mithrilButtons = m('button', {
                                'type':'button',
                                'class' : 'btn btn-default',
                                onclick : function(event) { ctrl.tb.modal.dismiss(); } }, 'Close');
                        ctrl.tb.modal.update(mithrilContent, mithrilButtons, m('h3.modal-title.break-word', 'How to Use the File Browser'));
                    },
                    icon: 'fa fa-info',
                    className : 'text-info'
                }, ''));
            }
        if (ctrl.tb.options.placement === 'fileview') {
            generalButtons.push(m.component(FGButton, {
                    onclick: function(event){
                        var panelToggle = $('.panel-toggle');
                        var panelExpand = $('.panel-expand');
                        var panelVisible = panelToggle.find('.osf-panel-hide');
                        var panelHidden = panelToggle.find('.osf-panel-show');

                        panelVisible.hide();
                        panelHidden.show();
                    },
                    icon: 'fa fa-angle-up'
                }, ''));
        }

        if (item && item.connected !== false){ // as opposed to undefined, avoids unnecessary setting of this value
            templates[toolbarModes.DEFAULT] = m('.col-xs-12', m('.pull-right', [finalRowButtons, m('span', generalButtons)]));
        } else {
            templates[toolbarModes.DEFAULT] = m('.col-xs-12', m('.pull-right', m('span', generalButtons)));
        }
        return m('.row.tb-header-row', [
            m('#folderRow', { config : function () {
                $('#folderRow input').focus();
            }}, [
                templates[ctrl.mode()]
            ])
        ]);
    }
};

/**
 * When multiple rows are selected remove those that are not valid
 * @param {Array} rows List of item objects
 * @returns {Array} newRows Returns the revised list of rows
 */
function filterRows(rows) {
    if(rows.length === 0){
        return;
    }
    var tb = this;
    var i, newRows = [],
        originalRow = tb.find(tb.multiselected()[0].id),
        originalParent,
        currentItem;
    function changeColor() { $(this).css('background-color', ''); }
    if (originalRow !== undefined) {
        originalParent = originalRow.parentID;
        for (i = 0; i < rows.length; i++) {
            currentItem = rows[i];
            // Filter rows that are no in the parent
            var inParent = currentItem.parentID === originalParent && currentItem.id !== -1;
            var inProgress = typeof currentItem.inProgress !== 'undefined' && currentItem.inProgress;
            if (inParent && !inProgress) {
                newRows.push(rows[i]);
            } else {
                $('.tb-row[data-id="' + rows[i].id + '"]').stop().css('background-color', '#D18C93')
                    .animate({ backgroundColor: '#fff'}, 500, changeColor);
                if (inProgress) {
                    $osf.growl('Error', 'Please wait for current action to complete');
                }
            }
        }
    }
    tb.multiselected(newRows);
    tb.highlightMultiselect();
    return newRows;
}

/**
 * Helper function that turns parent open values to true to respective redraws can open the folder
 * @this Treebeard.controller
 * @param {Object} item A Treebeard _item object.
 * @private
 */
function openParentFolders (item) {
    var tb = this;
    // does it have a parent? If so change open
    var parent = item.parent();
    if (parent) {
        if (!parent.open) {
            var index = tb.returnIndex(parent.id);
            parent.load = true;
            tb.toggleFolder(index);
        }
        openParentFolders.call(tb, parent);
    }
}

/**
 * Handles multiselect conditions and actions
 * @this Treebeard.controller
 * @param {Object} event jQuery click event.
 * @param {Object} row A Treebeard _item object.
 * @private
 */
 function _fangornMultiselect (event, row) {
    var tb = this;
    var scrollToItem = false;
    if (tb.toolbarMode() === 'filter') {
        scrollToItem = true;
        // recursively open parents of the selected item but do not lazyload;
        openParentFolders.call(tb, row);
    }
    dismissToolbar.call(tb);
    filterRows.call(tb, tb.multiselected());

    if (tb.multiselected().length === 1){
        tb.select('#tb-tbody').removeClass('unselectable');
        if(scrollToItem) {
             scrollToFile.call(tb, tb.multiselected()[0].id);
        }
    } else if (tb.multiselected().length > 1) {
        tb.select('#tb-tbody').addClass('unselectable');
    }
    m.redraw();
    reapplyTooltips();
}

/* BEGIN MOVE */
// copyMode can be 'copy', 'move', 'forbidden', or null.
// This is set at draglogic and is used as global within this module
var copyMode = null;

// Set altkey global to fangorn
    var altKey = false;
    $(document).keydown(function (e) {
        if (e.altKey) {
            altKey = true;
        }
    });
    $(document).keyup(function (e) {
        if (!e.altKey) {
            altKey = false;
        }
    });

/**
 * Hook for the drag start event on jquery
 * @param event jQuery UI drggable event object
 * @param ui jQuery UI draggable ui object
 * @private
 */
function _fangornDragStart(event, ui) {
    // Sync up the toolbar in case item was drag-clicked and not released
    m.redraw();
    var itemID = $(event.target).attr('data-id'),
        item = this.find(itemID);
    if (this.multiselected().length < 2) {
        this.multiselected([item]);
    }
}

/**
 * Hook for the drop event of jQuery UI droppable
 * @param event jQuery UI droppable event object
 * @param ui jQuery UI droppable ui object
 * @private
 */
function _fangornDrop(event, ui) {
    var tb = this;
    var items = tb.multiselected().length === 0 ? [tb.find(tb.selected)] : tb.multiselected(),
        folder = tb.find($(event.target).attr('data-id'));

    // Run drop logic here
        _dropLogic.call(tb, event, items, folder);
}

/**
 * Hook for the over event of jQuery UI droppable
 * @param event jQuery UI droppable event object
 * @param ui jQuery UI droppable ui object
 * @private
 */
function _fangornOver(event, ui) {
    var tb = this;
    var items = tb.multiselected().length === 0 ? [tb.find(tb.selected)] : tb.multiselected(),
        folder = tb.find($(event.target).attr('data-id')),
        dragState = _dragLogic.call(tb, event, items, ui);
    $('.tb-row').removeClass('tb-h-success fangorn-hover');
    if (dragState !== 'forbidden') {
        $('.tb-row[data-id="' + folder.id + '"]').addClass('tb-h-success');
    } else {
        $('.tb-row[data-id="' + folder.id + '"]').addClass('fangorn-hover');
    }
}

/**
 * Log the success or failure of a file action (upload, etc.) in treebeard
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @param success Boolean on whether upload actually happened
 * @param message String failure reason message, '' if success === true
 * @param link String with url to file, '' if success === false
 * @param op String specifying type of move conflict resolution; ['keep', 'skip', 'replace']
 * @private
 */
function addFileStatus(treebeard, file, success, message, link, op){
    if (typeof op !== 'undefined'){
        treebeard.moveStates.push(
            {'name': file.data.name, 'success': success, 'link': link, 'op': op}
        );
    } else {
        treebeard.uploadStates.push(
            {'name': file.name, 'success': success, 'link': link, 'message': message}
        );
    }

}

/**
 * Triggers file status modal or growlboxes after upload queue is empty
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @private
 */
var UPLOAD_MODAL_MIN_FILE_QUANTITY = 4;
function _fangornQueueComplete(treebeard) {
    var fileStatuses = treebeard.uploadStates;
    treebeard.uploadStates = [];
    var total = fileStatuses.length;
    var failed = 0;
    if (total >= UPLOAD_MODAL_MIN_FILE_QUANTITY) {
        treebeard.modal.update(m('', [
            m('', [
                fileStatuses.map(function(status){
                    if (!status.success){ failed++; }
                    return m('',
                        [
                            m('.row', [
                                m((status.success ? 'a[href="' + status.link + '"]' : '') + '.col-sm-10', status.name),
                                m('.col-sm-1', m(status.success ? '.fa.fa-check[style="color: green"]' : '.fa.fa-times[style="color: red"]')),
                                m('.col-sm-1', m(!status.success ? '.fa.fa-info[data-toggle="tooltip"][data-placement="top"][title="'+ status.message +'"]' : ''))
                            ]),
                            m('hr')
                        ]
                    );
                })
            ])
        ]), m('', [
            m('a.btn.btn-primary', {onclick: function() {treebeard.modal.dismiss();}}, 'Done'), //jshint ignore:line
        ]), m('', [m('h3.break-word.modal-title', 'Upload Status'), m('p', total - failed + '/' + total + ' files succeeded.')]));
        $('[data-toggle="tooltip"]').tooltip();
    } else {
        fileStatuses.map(function(status) {
           if (!status.success) {
                if (status.message !== 'Upload canceled.') {
                    $osf.growl(
                        'Error',
                        status.message
                    );
                }
           }
        });
    }
}

/**
 * Where the drop actions happen
 * @param event jQuery UI drop event
 * @param {Array} items List of items being dragged at the time. Each item is a _item object
 * @param {Object} folder Folder information as _item object
 */
function _dropLogic(event, items, folder) {
    var tb = this;

    if (items.length < 1 ||
        items.indexOf(folder) > -1 ||
        copyMode === 'forbidden'
    ) {
        return;
    }

    if (folder.data.kind === 'file') {
        folder = folder.parent();
    }

    if (!folder.open) {
        return tb.updateFolder(null, folder, _dropLogic.bind(tb, event, items, folder));
    }

    var toMove = checkConflicts(items, folder);

    tb.syncFileMoveCache = tb.syncFileMoveCache || {};
    tb.syncFileMoveCache[folder.data.provider] = tb.syncFileMoveCache[folder.data.provider] || {};
    tb.moveStates = [];

    if (toMove.ready.length > 0) {
        tb.syncFileMoveCache[folder.data.provider].ready = tb.syncFileMoveCache[folder.data.provider].ready || [];
        if (SYNC_UPLOAD_ADDONS.indexOf(folder.data.provider) !== -1) {
            toMove.ready.forEach(function(item) {
                tb.syncFileMoveCache[folder.data.provider].ready.push({'item' : item, 'folder' : folder});
            });
        } else {
            toMove.ready.forEach(function(item) {
                doItemOp.call(tb, copyMode === 'move' ? OPERATIONS.MOVE : OPERATIONS.COPY, folder, item, undefined, 'replace');
            });
        }
    }

    if (toMove.conflicts.length > 0) {
        tb.syncFileMoveCache[folder.data.provider].conflicts = tb.syncFileMoveCache[folder.data.provider].conflicts || [];
        toMove.conflicts.forEach(function(item) {
            tb.syncFileMoveCache[folder.data.provider].conflicts.push({'item' : item, 'folder' : folder});
        });
    }

    if (tb.syncFileMoveCache[folder.data.provider].conflicts ||
        tb.syncFileMoveCache[folder.data.provider].ready) {
        doSyncMove(tb, folder.data.provider);
    }
}

function displayMoveStats(tb) {
   var moveStatuses = tb.moveStates;
   var total = moveStatuses && moveStatuses.length;
   if (moveStatuses.length) {
       tb.moveStates = [];
       var failed = 0;
       var skipped = 0;
       tb.modal.update(m('', [
           m('', [
               moveStatuses.map(function(status){
                  if (!status.success){
                      failed++;
                  }
                  if (status.op === 'skip'){
                      skipped++;
                  }
                  return m('',
                       [
                           m('.row', [
                               m((status.success ? 'a[href="' + status.link + '"]' : '') + '.col-sm-7', status.name),
                               m('.col-sm-1', m(status.success ? '.fa.fa-check.text-success' : '.fa.fa-times.text-danger')),
                               m('.col-sm-4' + (status.success ? '.text-info' : '.text-danger'), CONFLICT_INFO[status.op].passed)
                           ]),
                           m('hr')
                       ]
                   );
               })
           ])
       ]), m('', [
           m('a.btn.btn-primary', {onclick: function() {tb.modal.dismiss();}}, 'Done'), //jshint ignore:line
       ]), m('', [
              m('h3.break-word.modal-title', 'Move Status'),
              m('p', [
                  m('span', failed !== total ? total - failed + '/' + total + ' files successfully moved.': ''),
                  m('span', skipped ? ' Skipped ' + skipped + '/' + total + ' files.': '')
                ])
      ]));
    } else {
        tb.modal.dismiss();
    }

}

function doSyncMove(tb, provider){
    var cache = tb.syncFileMoveCache && tb.syncFileMoveCache[provider];
    var itemData;
    if (cache.conflicts && cache.conflicts.length > 0) {
        itemData = cache.conflicts.pop();
        displayConflict(tb, itemData.item, itemData.folder, doItemOp.bind(tb, copyMode === 'move' ? OPERATIONS.MOVE : OPERATIONS.COPY, itemData.folder, itemData.item, undefined));
    } else if (cache.ready && cache.ready.length > 0) {
        itemData = cache.ready.pop();
        doItemOp.call(tb, copyMode === 'move' ? OPERATIONS.MOVE : OPERATIONS.COPY, itemData.folder, itemData.item, undefined, 'replace');
    } else {
        displayMoveStats(tb);
    }
}

/**
 * Sets the copy state based on which item is being dragged on which other item
 * @param {Object} event Browser drag event
 * @param {Array} items List of items being dragged at the time. Each item is a _item object
 * @param {Object} ui jQuery UI draggable drag ui object
 * @returns {String} copyMode One of the copy states, from 'copy', 'move', 'forbidden'
 */
function _dragLogic(event, items, ui) {
    var tb = this;
    var canMove = true,
    folder = this.find($(event.target).attr('data-id')),
    dragGhost = $('.tb-drag-ghost');

    // Set the cursor to match the appropriate copy mode
    copyMode = getCopyMode(folder, items);
    switch (copyMode) {
        case 'forbidden':
            dragGhost.css('cursor', 'not-allowed');
            break;
        case 'copy':
            dragGhost.css('cursor', 'copy');
            break;
        case 'move':
            dragGhost.css('cursor', 'move');
            break;
        default:
            dragGhost.css('cursor', 'default');
    }
    return copyMode;

}

function getAllChildren(item) {
    var c;
    var current;
    var children = [];
    var remaining = [];
    for (c in item.children) {
        remaining.push(item.children[c]);
    }
    while (remaining.length > 0) {
        current = remaining.pop();
        children.push(current);
        for (c in current.children) {
            remaining.push(current.children[c]);
        }
    }
    return children;
}

function isInvalidDropFolder(folder) {
    if (
        // cannot drop on root line
        folder.parentID === 0 ||
        // don't drop if changed
        folder.inProgress ||
        // cannot drop on files
        folder.data.nodeType ||
        folder.data.kind !== 'folder' ||
        // must have permission
        !folder.data.permissions.edit ||
        // must have a provider
        !folder.data.provider ||
        folder.data.status ||
        // cannot add to published dataverse
        (folder.data.provider === 'dataverse' && folder.data.dataverseIsPublished) ||
        // no dropping into read-only providers
        (READ_ONLY_ADDONS.indexOf(folder.data.provider) !== -1)
    ) {
        return true;
    }
    return false;
}

function isInvalidDropItem(folder, item, cannotBeFolder, mustBeIntra) {
    if (
        // not a valid drop if is a node
        item.data.nodeType ||
        // cannot drop on roots
        item.data.isAddonRoot ||
        // no self drops
        item.id === folder.id ||
        // no dropping on direct parent
        item.parentID === folder.id ||
        // no moving published items from dataverse
        (item.data.provider === 'dataverse' && item.data.extra.hasPublishedVersion) ||
        // no moving folders into dataverse
        (folder.data.provider === 'dataverse' && item.data.kind === 'folder') ||
        // no dropping if waiting on waterbutler ajax
        item.inProgress ||
        (cannotBeFolder && item.data.kind === 'folder') ||
        (mustBeIntra && item.data.provider !== folder.data.provider)
    ) {
        return true;
    }
    return false;
}

function allowedToMove(folder, item, mustBeIntra) {
    return (
        item.data.permissions.edit &&
        (!mustBeIntra || (item.data.provider === folder.data.provider && item.data.nodeId === folder.data.nodeId)) &&
        !(item.data.provider === 'figshare' && item.data.extra && item.data.extra.status === 'public') &&
        (READ_ONLY_ADDONS.indexOf(item.data.provider) === -1) && (READ_ONLY_ADDONS.indexOf(folder.data.provider) === -1)
    );
}

function folderContainsPreprint(item, preprintPath) {
    // TODO This will only get children of open folders  -ajs
    var children = getAllChildren(item);
    for (var c = 0; c < children.length; c++) {
        if (children[c].data.path === preprintPath) {
            return true;
        }
    }
    return false;
}

function showDeleteMultiple(items) {
    // Only show delete button if user has edit permissions on at least one selected file
    for (var i = 0; i < items.length; i++) {
        var each = items[i].data;
        if (typeof each.permissions !== 'undefined' && each.permissions.edit && !each.isAddonRoot && !each.nodeType) {
            return true;
        }
    }
    return false;
}

function multiselectContainsPreprint(items, preprintPath) {
    for (var i = 0; i < items.length; i++) {
        var each = items[i];
        if (each.data.kind === 'folder') {
            if (folderContainsPreprint(each, preprintPath)) {
                return true;
            }
        } else if (each.data.path === preprintPath) {
            return true;
        }
    }
    return false;
}

function getPreprintPath(preprintFileId) {
    if (preprintFileId) {
        return '/' + preprintFileId;
    }
    return null;
}

function getCopyMode(folder, items) {
    var tb = this;
    // Prevents side effects from rare instance where folders not fully populated
    if (typeof folder === 'undefined' || typeof folder.data === 'undefined') {
        return 'forbidden';
    }

    var preprintPath = getPreprintPath(window.contextVars.node.preprintFileId);
    var canMove = true;
    var mustBeIntra = (folder.data.provider === 'github');
    // Folders cannot be copied to dataverse at all.  Folders may only be copied to figshare
    // if the target is the addon root and the root is a project (not a fileset)
    var cannotBeFolder = (
        folder.data.provider === 'dataverse' ||
            (folder.data.provider === 'figshare' &&
             !(folder.data.isAddonRoot && folder.data.rootFolderType === 'project'))
    );
    if (isInvalidDropFolder(folder)) {
        return 'forbidden';
    }

    for (var i = 0; i < items.length; i++) {
        var item = items[i];
        if (isInvalidDropItem(folder, item, cannotBeFolder, mustBeIntra)) {
            return 'forbidden';
        }

        var children = getAllChildren(item);
        for (var c = 0; c < children.length; c++) {
            if (children[c].inProgress || children[c].id === folder.id) {
                return 'forbidden';
            }
            if (children[c].data.path === preprintPath){
                mustBeIntra = true;
            }
        }

        if (canMove) {
            mustBeIntra = mustBeIntra || item.data.provider === 'github' || preprintPath === item.data.path;
            canMove = allowedToMove(folder, item, mustBeIntra);
        }
    }

    if (folder.data.isPointer || altKey || !canMove) {
        return 'copy';
    }
    return 'move';
}
/* END MOVE */


function _resizeHeight () {
    var tb = this;
    var tbody = tb.select('#tb-tbody');
    var windowHeight = $(window).height();
    var topBuffer = tbody.offset().top + 50;
    var availableSpace = windowHeight - topBuffer;
    if(availableSpace > 0) {
        // Set a minimum height
        tbody.height(availableSpace < 300 ? 300 : availableSpace);
    }
}

/**
 * OSF-specific Treebeard options common to all addons.
 * Check Treebeard API for more information
 */
tbOptions = {
    rowHeight : 35,         // user can override or get from .tb-row height
    showTotal : 15,         // Actually this is calculated with div height, not needed. NEEDS CHECKING
    paginate : false,       // Whether the applet starts with pagination or not.
    paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
    uploads : true,         // Turns dropzone on/off.
    columnTitles : _fangornColumnTitles,
    resolveRows : _fangornResolveRows,
    lazyLoadPreprocess: waterbutler.wbLazyLoadPreprocess,
    hoverClassMultiselect : 'fangorn-selected',
    multiselect : true,
    placement : 'files',
    title : function() {
        //TODO Add disk saving mode message
        // if(window.contextVars.diskSavingMode) {
        //     // If File and FileRead are not defined dropzone is not supported and neither is uploads
        //     if (window.File && window.FileReader) {
        //         return m('p', {
        //         }, [
        //             m('span', 'To Upload: Drag files into a folder OR click the '),
        //             m('i.btn.btn-default.btn-xs', { disabled : 'disabled'}, [ m('i.fa.fa-upload')]),
        //             m('span', ' below.')
        //         ]);
        //     }
        //     return m('p', {
        //         class: 'text-danger'
        //     }, [
        //         m('span', 'Your browser does not support file uploads, ', [
        //             m('a', { href: 'http://browsehappy.com' }, 'learn more'),
        //             '.'
        //         ])
        //     ]);
        // }
        return undefined;
    },
    showFilter : true,      // Gives the option to filter by showing the filter box.
    allowMove : true,       // Turn moving on or off.
    hoverClass : 'fangorn-hover',
    togglecheck : _fangornToggleCheck,
    sortButtonSelector : {
        up : 'i.fa.fa-chevron-up',
        down : 'i.fa.fa-chevron-down'
    },
    ondataload: function() {
        _loadTopLevelChildren.call(this);
    },
    onload : function () {
        var tb = this;
        tb.options.onload = null;  // Make sure we don't get called again
        tb.uploadStates = [];
        tb.pendingFileOps = [];
        tb.select('#tb-tbody, .tb-tbody-inner').on('click', function(event){
            if(event.target !== this) {
                var item = tb.multiselected()[0];
                if (item) {
                    if (item.data.isAddonRoot || item.data.nodeType === 'project' || item.data.nodeType === 'component') {
                        tb.toolbarMode(toolbarModes.DEFAULT);
                    }
                    return;
                }
            }
            tb.clearMultiselect();
            m.redraw();
            dismissToolbar.call(tb);
        });
        $(window).on('beforeunload', function() {
            if(tb.dropzone && tb.dropzone.getUploadingFiles().length) {
                return 'You have pending uploads, if you leave this page they may not complete.';
            }
            if(tb.pendingFileOps.length > 0) {
                return 'You have pending file operations, if you leave this page they may not complete.';
            }
        });
        if(tb.options.placement === 'project-files') {
            _resizeHeight.call(tb);
            $(window).resize(function(){
                _resizeHeight.call(tb);
            });
        }
        $(window).on('keydown', function(event){
            if (event.keyCode === ESCAPE_KEY) {
                dismissToolbar.call(tb);
            }
        });
    },
    movecheck : function (to, from) { //This method gives the users an option to do checks and define their return
        return true;
    },
    movefail : function (to, from) { //This method gives the users an option to do checks and define their return
        return true;
    },
    addcheck : function (treebeard, item, file) {
        var size;
        var maxSize;
        var displaySize;
        var msgText;
        if (_fangornCanDrop(treebeard, item)) {
            if (item.data.accept && item.data.accept.maxSize) {
                size = file.size / 1000000;
                maxSize = item.data.accept.maxSize;
                if (size > maxSize) {
                    displaySize = Math.round(file.size / 10000) / 100;
                    msgText = 'One of the files is too large (' + displaySize + ' MB). Max file size is ' + item.data.accept.maxSize + ' MB.';
                    item.notify.update(msgText, 'warning', undefined, 3000);
                    addFileStatus(treebeard, file, false, 'File is too large. Max file size is ' + item.data.accept.maxSize + ' MB.', '');
                    return false;
                }
            }
            return true;
        }
        return false;
    },
    onscrollcomplete : function(){
        reapplyTooltips();
    },
    onmultiselect : _fangornMultiselect,
    filterPlaceholder : 'Filter',
    onmouseoverrow : _fangornMouseOverRow,
    sortDepth : 2,
    dropzone : {                                           // All dropzone options.
        maxFilesize: 10000000,
        url: function(files) {return files[0].url;},
        clickable : '#treeGrid',
        addRemoveLinks : false,
        previewTemplate : '<div></div>',
        parallelUploads : 5,
        acceptDirectories : false,
        createImageThumbnails : false,
        fallback: function(){},
    },
    resolveIcon : _fangornResolveIcon,
    resolveToggle : _fangornResolveToggle,
    // Pass ``null`` to avoid overwriting Dropzone URL resolver
    resolveUploadUrl: function() {return null;},
    resolveLazyloadUrl : _fangornResolveLazyLoad,
    resolveUploadMethod : _fangornUploadMethod,
    lazyLoadError : _fangornLazyLoadError,
    lazyLoadOnLoad : _fangornLazyLoadOnLoad,
    ontogglefolder : expandStateLoad,
    dropzoneEvents : {
        uploadprogress : _fangornUploadProgress,
        sending : _fangornSending,
        complete : _fangornComplete,
        success : _fangornDropzoneSuccess,
        removedfile: _fangornDropzoneRemovedFile,
        error : _fangornDropzoneError,
        dragover : _fangornDragOver,
        addedfile : _fangornAddedFile,
        drop : _fangornDropzoneDrop,
        queuecomplete : _fangornQueueComplete
    },
    resolveRefreshIcon : function() {
        return m('i.fa.fa-refresh.fa-spin');
    },
    removeIcon : function(){
        return m.trust('&times;');
    },
    toolbarComponent : FGToolbar,
    // DRAG AND DROP RELATED OPTIONS
    dragOptions : {},
    dropOptions : {},
    dragEvents : {
        start : _fangornDragStart
    },
    dropEvents : {
        drop : _fangornDrop,
        over : _fangornOver
    },
    onafterselectwitharrow : function(row, direction) {
        var tb = this;
        var item = tb.find(row.id);
        _fangornMultiselect.call(tb, null, item);
    },
    hScroll : null,
    naturalScrollLimit : 0
};

/**
 * Loads Fangorn with options
 * @param {Object} options The options to be extended with Treebeard options
 * @constructor
 */
function Fangorn(options) {
    this.options = $.extend({}, tbOptions, options);
    this.grid = null;       // Set by _initGrid
    this.init();
}

/**
 * Initialize Fangorn methods that connect it to Treebeard
 * @type {{constructor: Fangorn, init: Function, _initGrid: Function}}
 */
Fangorn.prototype = {
    constructor: Fangorn,
    init: function () {
        this._initGrid();
    },
    // Create the Treebeard once all addons have been configured
    _initGrid: function () {
        this.grid = new Treebeard(this.options);
        return this.grid;
    }
};

Fangorn.Components = {
    button : FGButton,
    input : FGInput,
    toolbar : FGToolbar,
    dropdown : FGDropdown,
    toolbarModes : toolbarModes
};

Fangorn.ButtonEvents = {
    _downloadEvent : _downloadEvent,
    _downloadZipEvent: _downloadZipEvent,
    _uploadEvent : _uploadEvent,
    _removeEvent : _removeEvent,
    createFolder : _createFolder,
    _gotoFileEvent : gotoFileEvent,
};

Fangorn.DefaultColumns = {
    _fangornTitleColumn : _fangornTitleColumn,
    _fangornVersionColumn : _fangornVersionColumn,
    _fangornModifiedColumn : _fangornModifiedColumn
};

Fangorn.Utils = {
    inheritFromParent : inheritFromParent,
    resolveconfigOption: resolveconfigOption,
    reapplyTooltips : reapplyTooltips,
    setCurrentFileID: setCurrentFileID,
    scrollToFile: scrollToFile,
    openParentFolders : openParentFolders,
    dismissToolbar : dismissToolbar,
    uploadRowTemplate : uploadRowTemplate,
    resolveIconView : resolveIconView,
    orderFolder : orderFolder,
    connectCheckTemplate : _connectCheckTemplate
};

Fangorn.DefaultOptions = tbOptions;

module.exports = {
    Fangorn : Fangorn,
    allowedToMove : allowedToMove,
    folderContainsPreprint : folderContainsPreprint,
    getAllChildren : getAllChildren,
    isInvalidDropFolder : isInvalidDropFolder,
    isInvalidDropItem : isInvalidDropItem,
    getCopyMode : getCopyMode,
    multiselectContainsPreprint : multiselectContainsPreprint,
    showDeleteMultiple : showDeleteMultiple,
    checkConflicts : checkConflicts
};

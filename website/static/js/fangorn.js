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

var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');

var iconmap = require('js/iconmap');

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

function cancelUploads (row) {
    var tb = this;
    var filesArr = tb.dropzone.getQueuedFiles();
    for (var i = 0; i < filesArr.length; i++) {
        var j = filesArr[i];
        if(!row){
            var parent = j.treebeardParent || tb.dropzoneItemCache;
            var item = findByTempID(parent, j.tmpID);
            tb.dropzone.removeFile(j);
            tb.deleteNode(parent.id,item.id);
        } else {
            tb.deleteNode(row.parentID,row.id);
            if(row.data.tmpID === j.tmpID){
                tb.dropzone.removeFile(j);
            }
        }
    }
    tb.isUploading(false);
}

var uploadRowTemplate = function(item){
    var tb = this;
    var padding;
    var progress = item.data.uploadState() === 'pending' ? 0 : Math.floor(item.data.progress);
    if (tb.filterOn) {
        padding = 20;
    } else {
        padding = (item.depth - 1) * 20;
    }
    var columns = [{
        data : '',  // Data field name
        css : '',
        custom : function(){ return m('row.text-muted', [
            m('.col-xs-7', {style: 'overflow: hidden;text-overflow: ellipsis;'}, [
                m('span', { style : 'padding-left:' + padding + 'px;'}, tb.options.resolveIcon.call(tb, item)),
                m('span',{ style : 'margin-left: 9px;'}, item.data.name)
            ]),
            m('.col-xs-3',
                m('.progress', [
                    m('.progress-bar.progress-bar-info.progress-bar-striped', {
                        role : 'progressbar',
                        'aria-valuenow' : progress,
                        'aria-valuemin' : '0',
                        'aria-valuemax': '100',
                        'style':'width: ' + progress + '%' }, m('span.sr-only', progress + '% Complete'))
                ])
            ),
            m('.col-xs-2', [
                m('span', m('.fangorn-toolbar-icon.m-l-sm', {
                        style : 'padding: 0px 6px 2px 2px;font-size: 16px;display: inline;',
                        config : function() {
                            reapplyTooltips();
                        },
                        'onclick' : function (e) {
                            e.stopImmediatePropagation();
                            cancelUploads.call(tb, item);
                        }},
                     m('span.text-muted','×')
                )),
            ]),

        ]); }
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
    var componentIcons = iconmap.componentIcons;
    var projectIcons = iconmap.projectIcons;
    function returnView(type, category) {
        var iconType = projectIcons[type];
        if (type === 'component' || type === 'registeredComponent') {
            if (!item.data.permissions.view) {
                return null;
            } else {
                iconType = componentIcons[category];
            }
        } else if (type === 'project' || type === 'registeredProject') {
            iconType = projectIcons[category];
        }
        if (type === 'registeredComponent' || type === 'registeredProject') {
            iconType += ' po-icon-registered';
        } else {
            iconType += ' po-icon';
        }
        var template = m('span', { 'class' : iconType});
        return template;
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
    var privateFolder =  m('div.file-extension._folder_delete', ' '),
        pointerFolder = m('i.fa.fa-link', ' '),
        openFolder  = m('i.fa.fa-folder-open', ' '),
        closedFolder = m('i.fa.fa-folder', ' '),
        configOption = item.data.provider ? resolveconfigOption.call(this, item, 'folderIcon', [item]) : undefined,  // jshint ignore:line
        icon;
    var newIcon = resolveIconView(item);
    if ( newIcon === null) {

        if (item.kind === 'folder') {
            if (item.data.iconUrl) {
                return m('span', {style: {width:'16px', height:'16px', background:'url(' + item.data.iconUrl+ ')', display:'block'}}, '');
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
        togglePlus = m('i.fa.fa-plus', ' ');
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

function checkConflicts(tb, item, folder, cb) {
    for(var i = 0; i < folder.children.length; i++) {
        var child = folder.children[i];
        if (child.data.name === item.data.name && child.id !== item.id) {
            tb.modal.update(m('', [
                m('h3.break-word', 'An item named "' + item.data.name + '" already exists in this location.'),
                m('p', 'Do you want to replace it?')
            ]), m('', [
                m('span.tb-modal-btn.text-default', {onclick: cb.bind(tb, 'keep')}, 'Keep Both'),
                m('span.tb-modal-btn.text-default', {onclick: function() {tb.modal.dismiss();}}, 'Cancel'), //jshint ignore:line
                m('span.tb-modal-btn.text-default', {onclick: cb.bind(tb, 'replace')},'Replace'),
            ]));
            return;
        }
    }
    cb('replace');
}

function checkConflictsRename(tb, item, name, cb) {
    var parent = item.parent();
    for(var i = 0; i < parent.children.length; i++) {
        var child = parent.children[i];
        if (child.data.name === name && child.id !== item.id) {
            tb.modal.update(m('', [
                m('h3.break-word', 'An item named "' + name + '" already exists in this location.'),
                m('p', 'Do you want to replace it?')
            ]), m('', [
                m('span.tb-modal-btn.text-default', {onclick: cb.bind(tb, 'keep')}, 'Keep Both'),
                m('span.tb-modal-btn.text-default', {onclick: function() {tb.modal.dismiss();}}, 'Cancel'), // jshint ignore:line
                m('span.tb-modal-btn.text-default', {onclick: cb.bind(tb, 'replace')},'Replace'),
            ]));
            return;
        }
    }
    cb('replace');
}

function doItemOp(operation, to, from, rename, conflict) {
    var tb = this;
    tb.modal.dismiss();
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


    $.ajax({
        type: 'POST',
        beforeSend: $osf.setXHRAuthorization,
        url: operation === OPERATIONS.COPY ? waterbutler.copyUrl() : waterbutler.moveUrl(),
        headers: {
            'Content-Type': 'Application/json'
        },
        data: JSON.stringify({
            'rename': rename,
            'conflict': conflict,
            'source': waterbutler.toJsonBlob(from),
            'destination': waterbutler.toJsonBlob(to),
        })
    }).done(function(resp, _, xhr) {
        if (to.data.provider === from.provider) {
            tb.pendingFileOps.pop();
        }
        if (xhr.status === 202) {
            var mithrilContent = m('div', [
                m('h3.break-word', operation.action + ' "' + from.data.materialized + '" to "' + (to.data.materialized || '/') + '" is taking a bit longer than expected.'),
                m('p', 'We\'ll send you an email when it has finished.'),
                m('p', 'In the mean time you can leave this page; your ' + operation.status + ' will still be completed.')
            ]);
            var mithrilButtons = m('div', [
                m('span.tb-modal-btn', { 'class' : 'text-default', onclick : function() { tb.modal.dismiss(); }}, 'OK')
            ]);
            tb.modal.update(mithrilContent, mithrilButtons);
            return;
        }
        from.data = resp;
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

        if (xhr.status !== 500 && xhr.responseJSON && xhr.responseJSON.message) {
            message = xhr.responseJSON.message;
        } else if (xhr.status === 503) {
            message = textStatus;
        } else {
            message = 'Please refresh the page or ' +
                'contact <a href="mailto: support@cos.io">support@cos.io</a> if the ' +
                'problem persists.';
        }

        $osf.growl(operation.verb + ' failed.', message);

        Raven.captureMessage('Failed to move or copy file', {
            xhr: xhr,
            requestData: {
                rename: rename,
                conflict: conflict,
                source: waterbutler.toJsonBlob(from),
                destination: waterbutler.toJsonBlob(to),
            }
        });

        orderFolder.call(tb, from.parent());
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
    var configOption = resolveconfigOption.call(this, item, 'uploadUrl', [item, file]); // jshint ignore:line
    return configOption || waterbutler.buildTreeBeardUpload(item, file);
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

    var item,
        child,
        templateWithCancel,
        templateWithoutCancel;
    for(var i = 0; i < parent.children.length; i++) {
        child = parent.children[i];
        if(!child.data.tmpID){
            continue;
        }
        if(child.data.tmpID === file.tmpID) {
            item = child;
            item.data.progress = progress;
            item.data.uploadState('uploading');
        }
    }
    m.redraw();
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
        uploadState : m.prop('pending')
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
        item.data = response;
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
    treebeard.redraw();
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
    // File may either be a webkit Entry or a file object, depending on the browser
    // On Chrome we can check if a directory is being uploaded
    var msgText;
    if (file.isDirectory) {
        msgText = 'Cannot upload directories, applications, or packages.';
    } else if (xhr.status === 507) {
        msgText = 'Cannot upload file due to insufficient storage.';
    } else {
        msgText = DEFAULT_ERROR_MESSAGE;
    }
    var parent = file.treebeardParent || treebeardParent.dropzoneItemCache; // jshint ignore:line
    // Parent may be undefined, e.g. in Chrome, where file is an entry object
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
    $osf.growl('Error', msgText);
    treebeard.options.uploadInProgress = false;
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
    var path = (parent.data.path || '/') + val + '/';

    if (parent.data.provider === 'github') {
        extra.branch = parent.data.branch;
    }

    m.request({
        method: 'POST',
        background: true,
        config: $osf.setXHRAuthorization,
        url: waterbutler.buildCreateFolderUrl(path, parent.data.provider, parent.data.nodeId)
    }).then(function(item) {
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
        tb.select('.tb-modal-footer .text-danger').html('<i> Deleting...</i>').css('color', 'grey');
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
        })
        .fail(function(data){
            tb.modal.dismiss();
            tb.clearMultiselect();
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
        if (folder.data.permissions.edit) {
                var mithrilContent = m('div', [
                        m('h3.break-word', 'Delete "' + folder.data.name+ '"?'),
                        m('p.text-danger', 'This folder and ALL its contents will be deleted. This action is irreversible.')
                    ]);
                var mithrilButtons = m('div', [
                        m('span.tb-modal-btn', { 'class' : 'text-primary', onclick : function() { cancelDelete.call(tb); } }, 'Cancel'),
                        m('span.tb-modal-btn', { 'class' : 'text-danger', onclick : function() { runDelete(folder); }  }, 'Delete')
                    ]);
                tb.modal.update(mithrilContent, mithrilButtons);
        } else {
            folder.notify.update('You don\'t have permission to delete this file.', 'info', undefined, 3000);
        }
    }

    // If there is only one item being deleted, don't complicate the issue:
    if(items.length === 1) {
        if(items[0].kind !== 'folder'){
            var mithrilContentSingle = m('div', [
                m('h3.break-word', 'Delete "' + items[0].data.name + '"'),
                m('p', 'This action is irreversible.')
            ]);
            var mithrilButtonsSingle = m('div', [
                m('span.tb-modal-btn', { 'class' : 'text-primary', onclick : function() { cancelDelete(); } }, 'Cancel'),
                m('span.tb-modal-btn', { 'class' : 'text-danger', onclick : function() { runDelete(items[0]); }  }, 'Delete')
            ]);
            // This is already being checked before this step but will keep this edit permission check
            if(items[0].data.permissions.edit){
                tb.modal.update(mithrilContentSingle, mithrilButtonsSingle);
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
                    m('h3.break-word', 'Delete multiple files?'),
                    deleteMessage,
                    deleteList.map(function(n){
                        if(n.kind === 'folder'){
                            return m('.fangorn-canDelete.text-success.break-word', [
                                m('i.fa.fa-folder'),m('b', ' ' + n.data.name)
                                ]);
                        }
                        return m('.fangorn-canDelete.text-success.break-word', n.data.name);
                    })
                ]);
            mithrilButtonsMultiple =  m('div', [
                    m('span.tb-modal-btn', { 'class' : 'text-primary', onclick : function() { tb.modal.dismiss(); } }, 'Cancel'),
                    m('span.tb-modal-btn', { 'class' : 'text-danger', onclick : function() { runDeleteMultiple.call(tb, deleteList); }  }, 'Delete All')
                ]);
        } else {
            mithrilContentMultiple = m('div', [
                    m('h3.break-word', 'Delete multiple files?'),
                    m('p', 'Some of these files can\'t be deleted but you can delete the ones highlighted with green. This action is irreversible.'),
                    deleteList.map(function(n){
                        if(n.kind === 'folder'){
                            return m('.fangorn-canDelete.text-success.break-word', [
                                m('i.fa.fa-folder'),m('b', ' ' + n.data.name)
                                ]);
                        }
                        return m('.fangorn-canDelete.text-success.break-word', n.data.name);
                    }),
                    noDeleteList.map(function(n){
                        return m('.fangorn-noDelete.text-warning.break-word', n.data.name);
                    })
                ]);
            mithrilButtonsMultiple =  m('div', [
                    m('span.tb-modal-btn', { 'class' : 'text-primary', onclick : function() {  tb.modal.dismiss(); } }, 'Cancel'),
                    m('span.tb-modal-btn', { 'class' : 'text-danger', onclick : function() { runDeleteMultiple.call(tb, deleteList); }  }, 'Delete Some')
                ]);
        }
        tb.modal.update(mithrilContentMultiple, mithrilButtonsMultiple);
    }
}

/**
 * Resolves lazy load url for fetching children
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {String|Boolean} Returns the fetch URL in string or false if there is no url.
 * @private
 */
function _fangornResolveLazyLoad(item) {
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
    var configOption = resolveconfigOption.call(this, item, 'lazyLoadError', [item]);
    if (!configOption) {
        item.notify.update('Files couldn\'t load. Please try again later.', 'deleting', undefined, 3000);
    }
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
    // Checking if this column does in fact have sorting
    var sortDirection = '';
    if (this.isSorted[0]) {
        sortDirection = this.isSorted[0].desc ? 'desc' : 'asc';
    } else {
        sortDirection = 'asc';
    }
    tree.sortChildren(this, sortDirection, 'text', 0, 1);
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


function gotoFileEvent (item) {
    var tb = this;
    var redir = new URI(item.data.nodeUrl);
    redir.segment('files').segment(item.data.provider).segmentCoded(item.data.path.substring(1));
    var fileurl  = redir.toString() + '/';
    if(COMMAND_KEYS.indexOf(tb.pressedKey) !== -1) {
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
function _fangornTitleColumn(item, col) {
    var tb = this;
    if (item.kind === 'file' && item.data.permissions.view) {
        return m('span.fg-file-links',{
            onclick: function(event) {
                event.stopImmediatePropagation();
                gotoFileEvent.call(tb, item);
            }
        }, item.data.name);
    }
    return m('span', item.data.name);
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
    var default_columns = [];
    var configOption;
    item.css = '';
    if(tb.isMultiselected(item.id)){
        item.css = 'fangorn-selected';
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
    default_columns.push(
    {
        data : 'name',  // Data field name
        folderIcons : true,
        filter : true,
        custom : _fangornTitleColumn
    });

    if (item.data.kind === 'file') {
        default_columns.push(
        {
            data : 'size',  // Data field name
            filter : true,
            custom : function() {return item.data.size ? $osf.humanFileSize(item.data.size, true) : '';}
        });
        if (item.data.provider === 'osfstorage') {
            default_columns.push({
                data : 'downloads',
                sortInclude : false,
                filter : false,
                custom: function() { return item.data.extra ? item.data.extra.downloads.toString() : ''; }
            });
        } else {
            default_columns.push({
                data : 'downloads',
                sortInclude : false,
                filter : false,
                custom : function() { return m(''); }
            });
        }
    }
    configOption = resolveconfigOption.call(this, item, 'resolveRows', [item]);
    return configOption || default_columns;
}

/**
 * Defines Column Titles separately since content and css may be different, allows more flexibility
 * @returns {Array} an Array of column information that gets templated inside Treebeard
 * @this Treebeard.controller
 * @private
 */
function _fangornColumnTitles () {
    var columns = [];
    columns.push(
    {
        title: 'Name',
        width : '80%',
        sort : true,
        sortType : 'text'
    }, {
        title : 'Size',
        width : '10%',
        sort : false
    }, {
        title : 'Downloads',
        width : '10%',
        sort : false
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
function expandStateLoad(item) {
    var tb = this,
        i;
    if (item.children.length > 0 && item.depth === 1) {
        for (i = 0; i < item.children.length; i++) {
            // if (item.children[i].data.isAddonRoot || item.children[i].data.addonFullName === 'OSF Storage' ) {
                tb.updateFolder(null, item.children[i]);
            // }
        }
    }
    if (item.children.length > 0 && item.depth === 2) {
        for (i = 0; i < item.children.length; i++) {
            if (item.children[i].data.isAddonRoot || item.children[i].data.addonFullName === 'OSF Storage' ) {
                tb.updateFolder(null, item.children[i]);
            }
        }
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
    checkConflictsRename(tb, item, val, doItemOp.bind(tb, OPERATIONS.RENAME, folder, item, val));
    tb.toolbarMode(toolbarModes.DEFAULT);
}

var toolbarModes = {
    'DEFAULT' : 'bar',
    'SEARCH' : 'search',
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
        return m('div', opts, [
            m('i', {className: iconCSS}),
            m('span', children)
        ]);
    }
};

var FGInput = {
    view : function(ctrl, args, helpText) {
        var extraCSS = args.className || '';
        var tooltipText = args.tooltip || '';
        var placeholder = args.placeholder || '';
        var id = args.id || '';
        var helpTextId = args.helpTextId || '';
        var onclick = args.onclick || noop;
        var onkeypress = args.onkeypress || noop;
        var value = args.value ? '[value="' + args.value + '"]' : '';
        return m('span', [
            m('input' + value, {
                'id' : id,
                className: 'tb-header-input' + extraCSS,
                onclick: onclick,
                onkeypress: onkeypress,
                'data-toggle':  tooltipText ? 'tooltip' : '',
                'title':  tooltipText,
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
            },[
                m('span.hidden-xs',label),
                m('select.no-border', {
                    'name' : name,
                    'id' : id,
                    onchange: onchange,
                    'data-toggle':  tooltipText ? 'tooltip' : '',
                    'title':  tooltipText,
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
        if (window.File && window.FileReader && item.kind === 'folder' && item.data.provider && item.data.permissions && item.data.permissions.edit) {
            rowButtons.push(
                m.component(FGButton, {
                    onclick: function(event) {_uploadEvent.call(tb, event, item); },
                    icon: 'fa fa-upload',
                    className : 'text-primary'
                }, 'Upload'),
                m.component(FGButton, {
                    onclick: function() {
                        mode(toolbarModes.ADDFOLDER);
                    },
                    icon: 'fa fa-plus',
                    className : 'text-primary'
                }, 'Create Folder'));
            if(item.data.path){
                rowButtons.push(
                    m.component(FGButton, {
                        onclick: function(event) {_removeEvent.call(tb, event, [item]); },
                        icon: 'fa fa-trash',
                        className : 'text-danger'
                    }, 'Delete Folder'));
            }
        }
        if (item.kind === 'file'){
            if (item.data.permissions && item.data.permissions.view) {
                rowButtons.push(
                    m.component(FGButton, {
                        onclick: function(event) {
                            gotoFileEvent.call(tb, item);
                        },
                        icon: 'fa fa-file-o',
                        className : 'text-info'
                    }, 'View'));
            }
            rowButtons.push(
                m.component(FGButton, {
                    onclick: function(event) { _downloadEvent.call(tb, event, item); },
                    icon: 'fa fa-download',
                    className : 'text-success'
                }, 'Download')
            );
            if (item.data.permissions && item.data.permissions.edit) {
                rowButtons.push(
                    m.component(FGButton, {
                        onclick: function(event) { _removeEvent.call(tb, event, [item]); },
                        icon: 'fa fa-trash',
                        className : 'text-danger'
                    }, 'Delete'));

            }
        } else if(item.data.provider && item.children.length !== 0) {
            rowButtons.push(
                m.component(FGButton, {
                    onclick: function(event) { _downloadZipEvent.call(tb, event, item); },
                    icon: 'fa fa-download',
                    className : 'text-success'
                }, 'Download as zip')
            );
        }
        if(item.data.provider && !item.data.isAddonRoot && item.data.permissions && item.data.permissions.edit) {
            rowButtons.push(
                m.component(FGButton, {
                    onclick: function() {
                        mode(toolbarModes.RENAME);
                    },
                    icon: 'fa fa-font',
                    className : 'text-info'
                }, 'Rename')
            );
        }
        return m('span', rowButtons);
    }
};

var dismissToolbar = function(){
    var tb = this;
    if (tb.toolbarMode() === toolbarModes.SEARCH){
        tb.resetFilter();
    }
    tb.toolbarMode(toolbarModes.DEFAULT);
    tb.filterText('');
    m.redraw();
};

var FGToolbar = {
    controller : function(args) {
        var self = this;
        self.tb = args.treebeard;
        self.tb.inputValue = m.prop('');
        self.tb.toolbarMode = m.prop(toolbarModes.DEFAULT);
        self.items = args.treebeard.multiselected;
        self.mode = self.tb.toolbarMode;
        self.isUploading = args.treebeard.isUploading;
        self.helpText = m.prop('');
        self.dismissToolbar = dismissToolbar.bind(self.tb);
        self.createFolder = function(event){
            _createFolder.call(self.tb, event, self.dismissToolbar, self.helpText );
        };
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
        templates[toolbarModes.SEARCH] =  [
            m('.col-xs-10', [
                ctrl.tb.options.filterTemplate.call(ctrl.tb)
                ]),
                m('.col-xs-2.tb-buttons-col',
                    m('.fangorn-toolbar.pull-right', [dismissIcon])
                )
            ];
        templates[toolbarModes.ADDFOLDER] = [
            m('.col-xs-9', [
                m.component(FGInput, {
                    onkeypress: function(event){
                        if (ctrl.tb.pressedKey === ENTER_KEY) {
                            _createFolder.call(ctrl.tb, event, ctrl.dismissToolbar);
                        }
                    },
                    id : 'createFolderInput',
                    helpTextId : 'createFolderHelp',
                    placeholder : 'New folder name',
                }, ctrl.helpText())
            ]),
            m('.col-xs-3.tb-buttons-col',
                m('.fangorn-toolbar.pull-right',
                    [
                        m.component(FGButton, {
                            onclick: ctrl.createFolder,
                            icon : 'fa fa-plus',
                            className : 'text-success'
                        }, 'Create'),
                        dismissIcon
                    ]
                )
            )
        ];
        templates[toolbarModes.RENAME] = [
            m('.col-xs-9',
                m.component(FGInput, {
                    onkeypress: function (event) {
                        ctrl.tb.inputValue($(event.target).val());
                        if (ctrl.tb.pressedKey === ENTER_KEY) {
                            _renameEvent.call(ctrl.tb);
                        }
                    },
                    id : 'renameInput',
                    helpTextId : 'renameHelpText',
                    placeholder : null,
                    value : ctrl.tb.inputValue(),
                }, ctrl.helpText())
            ),
            m('.col-xs-3.tb-buttons-col',
                m('.fangorn-toolbar.pull-right',
                    [
                        m.component(FGButton, {
                            onclick: function () {
                                _renameEvent.call(ctrl.tb);
                            },
                            icon : 'fa fa-pencil',
                            className : 'text-info'
                        }, 'Rename'),
                        dismissIcon
                    ]
                )
            )
        ];
        // Bar mode
        // Which buttons should show?
        if(items.length === 1){
            var addonButtons = resolveconfigOption.call(ctrl.tb, item, 'itemButtons', [item]);
            if (addonButtons) {
                finalRowButtons = m.component(addonButtons, { treebeard : ctrl.tb, item : item }); // jshint ignore:line
            } else {
                finalRowButtons = m.component(FGItemButtons, {treebeard : ctrl.tb, mode : ctrl.mode, item : item }); // jshint ignore:line
            }
        }
        if(ctrl.isUploading()){
            generalButtons.push(
                m.component(FGButton, {
                    onclick: function() {
                        cancelUploads.call(ctrl.tb);
                    },
                    icon: 'fa fa-time-circle',
                    className : 'text-danger'
                }, 'Cancel Pending Uploads')
            );
        }
        //multiple selection icons
        if(items.length > 1 && ctrl.tb.multiselected()[0].data.provider !== 'github') {
            var showDelete = false;
            // Only show delete button if user has edit permissions on at least one selected file
            for (var i = 0, len = items.length; i < len; i++) {
                var each = items[i];
                if (each.data.permissions.edit && !each.data.isAddonRoot && !each.data.nodeType) {
                    showDelete = true;
                    break;
                }
            }
            if(showDelete){
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
        generalButtons.push(
            m.component(FGButton, {
                onclick: function(event){
                    ctrl.mode(toolbarModes.SEARCH);
                },
                icon: 'fa fa-search',
                className : 'text-primary'
            }, 'Search'),
            m.component(FGButton, {
                onclick: function(event){
                    var mithrilContent = m('div', [
                        m('h3.break-word.m-b-lg', 'How to Use the File Browser'),
                        m('p', [ m('b', 'Select Rows:'), m('span', ' Click on a row (outside the name) to show further actions in the toolbar.')]),
                        m('p', [ m('b', 'Select Multiple Files:'), m('span', ' Use Command or Shift keys to select multiple files.')]),
                        m('p', [ m('b', 'Open Files:'), m('span', ' Click a file name to go to the file.')]),
                        m('p', [ m('b', 'Open Files in New Tab:'), m('span',  ' Press Command (or Ctrl in Windows) and  click a file name to open it in a new tab.')]),
                        m('p', [ m('b', 'Copy Files:'), m('span', ' Press Option (or Alt in Windows) while dragging a file to a new folder or component.')])
                    ]);
                    var mithrilButtons = m('div', [
                        m('span.tb-modal-btn', { 'class' : 'text-primary', onclick : function(event) { ctrl.tb.modal.dismiss(); } }, 'Close'),
                    ]);
                    ctrl.tb.modal.update(mithrilContent, mithrilButtons);
                },
                icon: 'fa fa-info',
                className : 'text-info'
            }, '')
        );

        templates[toolbarModes.DEFAULT] =  m('.col-xs-12', m('.pull-right', [finalRowButtons,  m('span', generalButtons)]));
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
 * When multiple rows are selected remove those that are not in the parent
 * @param {Array} rows List of item objects
 * @returns {Array} newRows Returns the revised list of rows
 */
function filterRowsNotInParent(rows) {
    var tb = this;
    if (tb.multiselected().length < 2) {
        return tb.multiselected();
    }
    var i, newRows = [],
        originalRow = tb.find(tb.multiselected()[0].id),
        originalParent,
        currentItem;
    function changeColor() { $(this).css('background-color', ''); }
    if (originalRow !== undefined) {
        originalParent = originalRow.parentID;
        for (i = 0; i < rows.length; i++) {
            currentItem = rows[i];
            if (currentItem.parentID === originalParent && currentItem.id !== -1) {
                newRows.push(rows[i]);
            } else {
                $('.tb-row[data-id="' + rows[i].id + '"]').stop().css('background-color', '#D18C93')
                    .animate({ backgroundColor: '#fff'}, 500, changeColor);
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
    if(parent ){
        if(!parent.open) {
            var index = tb.returnIndex(parent.id);
            parent.load = true;
            tb.toggleFolder(index);
        }
        openParentFolders.call(tb, parent);
    }
    return;
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
    filterRowsNotInParent.call(tb, tb.multiselected());
    if (tb.toolbarMode() === 'search') {
        dismissToolbar.call(tb);
        scrollToItem = true;
        // recursively open parents of the selected item but do not lazyload;
        openParentFolders.call(tb, row);
    }

    if (tb.multiselected().length === 1){
        tb.select('#tb-tbody').removeClass('unselectable');
        if(scrollToItem) {
             scrollToFile.call(tb, tb.multiselected()[0].id);
        }
    } else if (tb.multiselected().length > 1) {
        tb.select('#tb-tbody').addClass('unselectable');
    }
    tb.inputValue(tb.multiselected()[0].data.name);
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

    // if (items[0].data.kind === 'folder' && ['github', 'figshare', 'dataverse'].indexOf(folder.data.provider) !== -1) { return; }

    if (!folder.open) {
        return tb.updateFolder(null, folder, _dropLogic.bind(tb, event, items, folder));
    }

    $.each(items, function(index, item) {
        checkConflicts(tb, item, folder, doItemOp.bind(tb, copyMode === 'move' ? OPERATIONS.MOVE : OPERATIONS.COPY, folder, item, undefined));
    });
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

function getCopyMode(folder, items) {
    var tb = this;
    var canMove = true;
    var mustBeIntra = (folder.data.provider === 'github');
    var cannotBeFolder = (folder.data.provider === 'figshare' || folder.data.provider === 'dataverse');

    if (folder.data.kind === 'file') {
        folder = folder.parent();
    }

    if (folder.parentId === 0 ||
        folder.data.kind !== 'folder' ||
        !folder.data.permissions.edit ||
        !folder.data.provider ||
        folder.data.status ||
        folder.data.provider === 'dataverse'
    ) {
        return 'forbidden';
    }

    //Disallow moving INTO a public figshare folder
    if (
        folder.data.provider === 'figshare' &&
        folder.data.extra &&
        folder.data.extra.status &&
        folder.data.extra.status === 'public'
    ) {
        return 'forbidden';
    }

    for(var i = 0; i < items.length; i++) {
        var item = items[i];
        if (
            item.data.nodeType ||
            item.data.isAddonRoot ||
            item.id === folder.id ||
            item.parentID === folder.id ||
            item.data.provider === 'dataverse' ||
            (cannotBeFolder && item.data.kind === 'folder') ||
            (mustBeIntra && item.data.provider !== folder.data.provider) ||
            //Disallow moving OUT of a public figshare folder
            (item.data.provider === 'figshare' && item.data.extra && item.data.status && item.data.status !== 'public')
        ) {
            return 'forbidden';
        }

        mustBeIntra = mustBeIntra || item.data.provider === 'github';
        canMove = (
            canMove &&
            item.data.permissions.edit &&
            //Can only COPY OUT of figshare
            item.data.provider !== 'figshare' &&
            (!mustBeIntra || (item.data.provider === folder.data.provider && item.data.nodeId === folder.data.nodeId))
        );
    }
    if (folder.data.isPointer ||
        altKey ||
        !canMove
    ) {
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
        tbody.height(availableSpace);
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
    showFilter : true,     // Gives the option to filter by showing the filter box.
    allowMove : true,       // Turn moving on or off.
    hoverClass : 'fangorn-hover',
    togglecheck : _fangornToggleCheck,
    sortButtonSelector : {
        up : 'i.fa.fa-chevron-up',
        down : 'i.fa.fa-chevron-down'
    },
    onload : function () {
        var tb = this;
        _loadTopLevelChildren.call(tb);
        tb.pendingFileOps = [];
        tb.select('#tb-tbody').on('click', function(event){
            if(event.target !== this) {
                return;
            }
            tb.clearMultiselect();
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
    filterPlaceholder : 'Search',
    onmouseoverrow : _fangornMouseOverRow,
    sortDepth : 2,
    dropzone : {                                           // All dropzone options.
        url: function(files) {return files[0].url;},
        clickable : '#treeGrid',
        addRemoveLinks: false,
        previewTemplate: '<div></div>',
        parallelUploads: 1,
        acceptDirectories: false,
        fallback: function(){}
    },
    resolveIcon : _fangornResolveIcon,
    resolveToggle : _fangornResolveToggle,
    // Pass ``null`` to avoid overwriting Dropzone URL resolver
    resolveUploadUrl: function() {return null;},
    resolveLazyloadUrl : _fangornResolveLazyLoad,
    resolveUploadMethod: _fangornUploadMethod,
    lazyLoadError : _fangornLazyLoadError,
    lazyLoadOnLoad : _fangornLazyLoadOnLoad,
    ontogglefolder : expandStateLoad,
    dropzoneEvents : {
        uploadprogress : _fangornUploadProgress,
        sending : _fangornSending,
        complete : _fangornComplete,
        success : _fangornDropzoneSuccess,
        error : _fangornDropzoneError,
        dragover : _fangornDragOver,
        addedfile : _fangornAddedFile,
        drop : _fangornDropzoneDrop
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
        _fangornMultiselect.call(tb,null,item);
    },
    hScroll : 400,
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
    },
};

Fangorn.Components = {
    button : FGButton,
    input : FGInput,
    toolbar : FGToolbar,
    dropdown : FGDropdown,
    toolbarModes : toolbarModes
};

Fangorn.ButtonEvents = {
    _downloadEvent: _downloadEvent,
    _downloadZipEvent: _downloadZipEvent,
    _uploadEvent: _uploadEvent,
    _removeEvent: _removeEvent,
    createFolder: _createFolder,
    _gotoFileEvent : gotoFileEvent
};

Fangorn.DefaultColumns = {
    _fangornTitleColumn: _fangornTitleColumn
};

Fangorn.Utils = {
    inheritFromParent: inheritFromParent,
    resolveconfigOption: resolveconfigOption,
    reapplyTooltips : reapplyTooltips,
    setCurrentFileID: setCurrentFileID,
    scrollToFile: scrollToFile,
    openParentFolders : openParentFolders,
    dismissToolbar : dismissToolbar,
    uploadRowTemplate : uploadRowTemplate,
    resolveIconView: resolveIconView,
    orderFolder: orderFolder
};

Fangorn.DefaultOptions = tbOptions;

module.exports = Fangorn;

/**
 * Fangorn: Defining Treebeard options for OSF.
 * For Treebeard and _item API's check: https://github.com/caneruguz/treebeard/wiki
 */

'use strict';

var $ = require('jquery');
var m = require('mithril');
var Treebeard = require('treebeard');
var URI = require('URIjs');
var waterbutler = require('waterbutler');

var $osf = require('osfHelpers');

// CSS
require('../css/fangorn.css');

var tbOptions;

var tempCounter = 1;

/**
 * Returns custom icons for OSF depending on the type of item
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {Object}  Returns a mithril template with the m() function.
 * @private
 */
function _fangornResolveIcon(item) {
    var privateFolder = m('img', {src: '/static/img/hgrid/fatcowicons/folder_delete.png'}),
        pointerFolder = m('i.icon-link', ' '),
        openFolder  = m('i.icon-folder-open', ' '),
        closedFolder = m('i.icon-folder-close', ' '),
        configOption = item.data.provider ? resolveconfigOption.call(this, item, 'folderIcon', [item]) : undefined,  // jshint ignore:line
        ext,
        extensions;

    if (item.kind === 'folder') {
        if (item.data.iconUrl) {
            return m('img', { src : item.data.iconUrl, style: {width: '16px', height: 'auto'} });
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

    ext = item.data.name.split('.').pop().toLowerCase();
    extensions = ['3gp', '7z', 'ace', 'ai', 'aif', 'aiff', 'amr', 'asf', 'asx', 'bat', 'bin', 'bmp', 'bup',
        'cab', 'cbr', 'cda', 'cdl', 'cdr', 'chm', 'dat', 'divx', 'dll', 'dmg', 'doc', 'docx', 'dss', 'dvf', 'dwg',
        'eml', 'eps', 'exe', 'fla', 'flv', 'gif', 'gz', 'hqx', 'htm', 'html', 'ifo', 'indd', 'iso', 'jar',
        'jpeg', 'jpg', 'lnk', 'log', 'm4a', 'm4b', 'm4p', 'm4v', 'mcd', 'mdb', 'mid', 'mov', 'mp2', 'mp3', 'mp4',
        'mpeg', 'mpg', 'msi', 'mswmm', 'ogg', 'pdf', 'png', 'pps', 'ps', 'psd', 'pst', 'ptb', 'pub', 'qbb',
        'qbw', 'qxd', 'ram', 'rar', 'rm', 'rmvb', 'rtf', 'sea', 'ses', 'sit', 'sitx', 'ss', 'swf', 'tgz', 'thm',
        'tif', 'tmp', 'torrent', 'ttf', 'txt', 'vcd', 'vob', 'wav', 'wma', 'wmv', 'wps', 'xls', 'xpi', 'zip',
        'xlsx', 'py'];

    if (extensions.indexOf(ext) !== -1) {
        return m('img', { src : '/static/img/hgrid/fatcowicons/file_extension_' + ext + '.png'});
    }
    return m('i.icon-file-alt');
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
    fields = fields || inheritedFields;
    fields.forEach(function(field) {
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
    var toggleMinus = m('i.icon-minus', ' '),
        togglePlus = m('i.icon-plus', ' ');
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
        column,
        msgText = '';
    for(var i = 0; i < parent.children.length; i++) {
        child = parent.children[i];
        if(!child.data.tmpID){
            continue;
        }
        if(child.data.tmpID === file.tmpID) {
            item = child;
        }
    }

    if(treebeard.options.placement === 'dashboard'){
        column = null;
        msgText += file.name.slice(0,25) + '... : ';
    } else {
        column = 1;
    }
    msgText  += 'Uploaded ' + Math.floor(progress) + '%';

    if (progress < 100) {
        item.notify.update(msgText, 'success', column, 0);
    } else {
        item.notify.update(msgText, 'success', column, 2000);
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
        tmpID: tmpID
    };
    treebeard.createItem(blankItem, item.id);
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
        itemID =  parseInt(closestTarget.attr('data-id')),
        item = treebeard.find(itemID);
    $('.tb-row').removeClass(dropzoneHoverClass).removeClass(treebeard.options.hoverClass);
    if (item !== undefined) {
        if (_fangornCanDrop(treebeard, item)) {
            closestTarget.addClass(dropzoneHoverClass);
        }
    }
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
    _fangornOrderFolder.call(treebeard, item);
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
var DEFAULT_ERROR_MESSAGE = 'Could not upload file. The file may be invalid.';
function _fangornDropzoneError(treebeard, file, message) {
    // File may either be a webkit Entry or a file object, depending on the browser
    // On Chrome we can check if a directory is being uploaded
    var msgText;
    if (file.isDirectory) {
        msgText = 'Cannot upload directories, applications, or packages.';
    } else {
        msgText = DEFAULT_ERROR_MESSAGE;
    }
    var parent = file.treebeardParent || treebeard.dropzoneItemCache;
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
            item = child;
            treebeard.deleteNode(parent.id, item.id);
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

/**
 * Deletes the item, only appears for items
 * @param event DOM event object for click
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Information pertinent to that column where this upload event is run from
 * @private
 */
function _removeEvent (event, item, col) {
    try {
        event.stopPropagation();
    } catch (e) {
        window.event.cancelBubble = true;
    }
    var tb = this;

    function cancelDelete() {
        this.modal.dismiss();
    }
    function runDelete() {
        var tb = this;
        $('.tb-modal-footer .btn-success').html('<i> Deleting...</i>').attr('disabled', 'disabled');
        // delete from server, if successful delete from view
        var url = resolveconfigOption.call(this, item, 'resolveDeleteUrl', [item]);
        url = url || waterbutler.buildTreeBeardDelete(item);
        $.ajax({
            url: url,
            type: 'DELETE'
        })
        .done(function(data) {
            // delete view
            tb.deleteNode(item.parentID, item.id);
            tb.modal.dismiss();
        })
        .fail(function(data){
            tb.modal.dismiss();
            item.notify.update('Delete failed.', 'danger', undefined, 3000);
        });
    }

    if (item.data.permissions.edit) {
        var mithrilContent = m('div', [
                m('h3.break-word', 'Delete "' + item.data.name+ '"?'),
                m('p', 'This action is irreversible.')
            ]);
        var mithrilButtons = m('div', [
                m('button', { 'class' : 'btn btn-default m-r-md', onclick : function() { cancelDelete.call(tb); } }, 'Cancel'),
                m('button', { 'class' : 'btn btn-success', onclick : function() { runDelete.call(tb); }  }, 'OK')
            ]);
        tb.modal.update(mithrilContent, mithrilButtons);
    } else {
        item.notify.update('You don\'t have permission to delete this file.', 'info', undefined, 3000);
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
 * Checks if the file being uploaded exists by comparing name of existing children with file name
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} file File object that dropzone passes
 * @this Treebeard.controller
 * @returns {boolean}
 * @private
 */
// function _fangornFileExists(item, file) {
//     var i,
//         child;
//     for (i = 0; i < item.children.length; i++) {
//         child = item.children[i];
//         if (child.kind === 'file' && child.data.name === file.name) {
//             return true;
//         }
//     }
//     return false;
// }

/**
 * Handles errors in lazyload fetching of items, usually link is wrong
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _fangornLazyLoadError (item) {
    var configOption = resolveconfigOption.call(this, item, 'lazyLoadError', [item]);
    if (!configOption) {
        item.notify.update('Files couldn\'t load, please try again later.', 'deleting', undefined, 3000);
    }
}

/**
 * Called when new object data has arrived to be loaded.
 * @param {Object} tree A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _fangornLazyLoadOnLoad (tree) {
    tree.children.forEach(function(item) {
        inheritFromParent(item, tree);
    });
    resolveconfigOption.call(this, tree, 'lazyLoadOnLoad', [tree]);
    $('[data-toggle="tooltip"]').tooltip({container: 'body'});

    if (tree.depth > 1) {
        _fangornOrderFolder.call(this, tree);
    }
}

/**
 * Order contents of a folder without an entire sorting of all the table
 * @param {Object} tree A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _fangornOrderFolder(tree) {
    var sortDirection = this.isSorted[0].desc ? 'desc' : 'asc';
    tree.sortChildren(this, sortDirection, 'text', 0);
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


/**
 * Defines the contents for the action column, upload and download buttons etc.
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Options for this particulat column
 * @this Treebeard.controller
 * @returns {Array} Returns an array of mithril template objects using m()
 * @private
 */
function _fangornActionColumn (item, col) {
    var self = this,
        buttons = [];

    // Upload button if this is a folder
    // If File and FileRead are not defined dropzone is not supported and neither is uploads
    if (window.File && window.FileReader && item.kind === 'folder' && item.data.provider && item.data.permissions.edit) {
        buttons.push({
            name: '',
            icon: 'icon-upload-alt',
            'tooltip' : 'Upload files',

            css: 'fangorn-clickable btn btn-default btn-xs',
            onclick: _uploadEvent
        });
    }
    //Download button if this is an item
    if (item.kind === 'file') {
        buttons.push({
            'name' : '',
            'tooltip' : 'Download file',
            'icon' : 'icon-download-alt',
            'css' : 'btn btn-info btn-xs',
            'onclick' : _downloadEvent
        });
        if (item.data.permissions.edit) {
            buttons.push({
                'name' : '',
                'tooltip' : 'Delete',
                'icon' : 'icon-remove',
                'css' : 'm-l-lg text-danger fg-hover-hide',
                'style' : 'display:none',
                'onclick' : _removeEvent
            });
        }
    }
    // Build the template for icons
    return buttons.map(function (btn) {
        return m('span', { 'data-col' : item.id }, [ m('i',
            { 'class' : btn.css, 'data-toggle' : 'tooltip', title : btn.tooltip, 'data-placement': 'bottom', style : btn.style, 'onclick' : function(event) { btn.onclick.call(self, event, item, col); } },
            [ m('span', { 'class' : btn.icon}, btn.name) ])
            ]);
    });
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
    if (item.kind === 'file' && item.data.permissions.view) {
        return m('span',{
            onclick: function() {
                var redir = new URI(item.data.nodeUrl);
                redir.segment('files').segment(item.data.provider).segmentCoded(item.data.path.substring(1));
                window.location = redir.toString() + '/';
            },
            'data-toggle' : 'tooltip', title : 'View file', 'data-placement': 'right'
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
    var default_columns = [];
    var configOption;
    item.css = '';
    if(item.data.tmpID){
        return [
        {
            data : 'name',  // Data field name
            folderIcons : true,
            filter : true,
            custom : function(){ return m('span.text-muted', item.data.name); }
        },
        {
            data : '',  // Data field name
            custom : function(){ return m('span.text-muted', 'Upload pending...'); }
        },
        {
            data : '',  // Data field name
            custom : function(){ return m('span', ''); }
        }
        ];
    }

    if (item.parentID) {
        item.data.permissions = item.data.permissions || item.parent().data.permissions;
        if (item.data.kind === 'folder') {
            item.data.accept = item.data.accept || item.parent().data.accept;
        }
    }

    default_columns.push({
        data : 'name',  // Data field name
        folderIcons : true,
        filter : true,
        custom : _fangornTitleColumn
    });
    var actionColumn = (
        resolveconfigOption.call(this, item, 'resolveActionColumn', [item]) ||
        _fangornActionColumn
    );
    default_columns.push({
        sortInclude : false,
        custom : actionColumn
    });
    if (item.data.provider === 'osfstorage' && item.data.kind === 'file') {
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
    columns.push({
        title: 'Name',
        width : '65%',
        sort : true,
        sortType : 'text'
    }, {
        title : 'Actions',
        width : '20%',
        sort : false
    }, {
        title : 'Downloads',
        width : '15%',
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
    $('[data-toggle="tooltip"]').tooltip({container: 'body'});
}


/**
 * OSF-specific Treebeard options common to all addons.
 * Check Treebeard API for more information
 */
tbOptions = {
    rowHeight : 30,         // user can override or get from .tb-row height
    showTotal : 15,         // Actually this is calculated with div height, not needed. NEEDS CHECKING
    paginate : false,       // Whether the applet starts with pagination or not.
    paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
    uploads : true,         // Turns dropzone on/off.
    columnTitles : _fangornColumnTitles,
    resolveRows : _fangornResolveRows,
    title : function() {
        if(window.contextVars.uploadInstruction) {
            // If File and FileRead are not defined dropzone is not supported and neither is uploads
            if (window.File && window.FileReader) {
                return m('p', {
                }, [
                    m('span', 'To Upload: Drag files into a folder below OR click the '),
                    m('i.btn.btn-default.btn-xs', { disabled : 'disabled'}, [ m('span.icon-upload-alt')]),
                    m('span', ' below.')
                ]);
            }
            return m('p', {
                class: 'text-danger'
            }, [
                m('span', 'Your browser does not support file uploads, ', [
                    m('a', { href: 'http://browsehappy.com' }, 'learn more'),
                    '.'
                ])
            ]);
        }
        return undefined;
    },
    showFilter : true,     // Gives the option to filter by showing the filter box.
    allowMove : false,       // Turn moving on or off.
    hoverClass : 'fangorn-hover',
    togglecheck : _fangornToggleCheck,
    sortButtonSelector : {
        up : 'i.icon-chevron-up',
        down : 'i.icon-chevron-down'
    },
    onload : function () {
        var tb = this;
        _loadTopLevelChildren.call(tb);
        $(document).on('click', '.fangorn-dismiss', function() {
            tb.redraw();
        });

        $(window).on('beforeunload', function() {
            if (tb.dropzone && tb.dropzone.getUploadingFiles().length) {
              return 'You have pending uploads, if you leave this page they may not complete.';
            }
        });
    },
    createcheck : function (item, parent) {
        return true;
    },
    deletecheck : function (item) {  // When user attempts to delete a row, allows for checking permissions etc.
        return true;
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
        $('[data-toggle="tooltip"]').tooltip({container: 'body'});
    },
    onselectrow : function(row) {
    },
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
        addedfile : _fangornAddedFile
    }
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

Fangorn.ButtonEvents = {
    _downloadEvent: _downloadEvent,
    _uploadEvent: _uploadEvent,
    _removeEvent: _removeEvent
};

Fangorn.DefaultColumns = {
    _fangornTitleColumn: _fangornTitleColumn
};

Fangorn.Utils = {
    inheritFromParent: inheritFromParent,
    resolveconfigOption: resolveconfigOption
};

module.exports = Fangorn;

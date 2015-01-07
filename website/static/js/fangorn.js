/**
 * Fangorn: Defining Treebeard options for OSF.
 * For Treebeard and _item API's check: https://github.com/caneruguz/treebeard/wiki
 */

var $ = require('jquery');
var m = require('mithril');
var Treebeard = require('treebeard');
var waterbutler = require('waterbutler');

var tbOptions;


/**
 * Returns custom icons for OSF depending on the type of item
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {Object}  Returns a mithril template with the m() function.
 * @private
 */
function _fangornResolveIcon(item) {
    var privateFolder = m('img', { src : '/static/img/hgrid/fatcowicons/folder_delete.png' }),
        pointerFolder = m('i.icon-hand-right', ' '),
        openFolder  = m('i.icon-folder-open-alt', ' '),
        closedFolder = m('i.icon-folder-close-alt', ' '),
        configOption = item.data.provider ? resolveconfigOption.call(this, item, 'folderIcon', [item]) : undefined,
        ext,
        extensions;

    if (item.kind === 'folder') {
        if (item.data.iconUrl) {
            return m('img', { src : item.data.iconUrl, style: {width: "16px", height: "auto"} });
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
    var self = this,
        prop = getconfig(item, option);
    if (prop) {
        return typeof prop === 'function' ? prop.apply(self, args) : prop;
    }
    return null;
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
    if (item.kind === 'folder') {
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
    var configOption = resolveconfigOption.call(this, item, 'uploadUrl', [item, file]);
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
    var item = treebeard.dropzoneItemCache.children[0],
        msgText = 'Uploaded ' + Math.floor(progress) + '%';

    if (progress < 100) {
        item.notify.update(msgText, 'success', 1, 0);
    } else {
        item.notify.update(msgText, 'success', 1, 2000);
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
    var parentID = treebeard.dropzoneItemCache.id,
        parent = treebeard.dropzoneItemCache,
        configOption,
        blankItem = {       // create a blank item that will refill when upload is finished.
            name : file.name,
            kind : 'file',
            provider : parent.data.provider,
            children : [],
            data : {}
        };
    treebeard.createItem(blankItem, parentID);

    var _send = xhr.send;
    xhr.send = function() {
        _send.call(xhr, file);
    };

    configOption = resolveconfigOption.call(treebeard, parent, 'uploadSending', [file, xhr, formData]);
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
    var item = treebeard.dropzoneItemCache,
        configOption = resolveconfigOption.call(treebeard, item, 'uploadAdd', [file, item]);

    file.url = _fangornResolveUploadUrl(item, file);
    file.method = _fangornUploadMethod(item);

    return configOption || null;
}

/**
 * Runs when Dropzone's dragover event hook is run.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param event DOM event object
 * @this Dropzone
 * @private
 */
function _fangornDragOver(treebeard, event) {
    var dropzoneHoverClass = "fangorn-dz-hover",
        closestTarget = $(event.target).closest('.tb-row'),
        itemID =  closestTarget.context.dataset.id,
        item = treebeard.find(itemID);
    $('.tb-row').removeClass(dropzoneHoverClass);
    if (itemID !== undefined) {
        if (item.data.provider && item.kind === 'folder') {
            $(event.target).closest('.tb-row').addClass(dropzoneHoverClass);
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
    var item = treebeard.dropzoneItemCache;
    resolveconfigOption.call(treebeard, item, 'onUploadComplete', [item]);
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
    var item,
        revisedItem;
    item = treebeard.dropzoneItemCache.children[0];
    // RESPONSES
    // OSF : Object with actionTake : "file_added"
    // DROPBOX : Object; addon : 'dropbox'
    // S3 : Nothing
    // GITHUB : Object; addon : 'github'
    // Dataverse : Object, actionTaken : file_uploaded
    revisedItem = resolveconfigOption.call(treebeard, item.parent(), 'uploadSuccess', [file, item, response]);
    if (!revisedItem && response) {
        item.data = response;
        item.data.permissions = item.parent().data.permissions;
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
function _fangornDropzoneError(treebeard, file, message) {
    var item = treebeard.dropzoneItemCache.children[0],
        msgText = message.message_short || message;
    item.notify.type = 'danger';
    item.notify.message = msgText;
    item.notify.col = 1;
    item.notify.selfDestruct(treebeard, item);
}

/**
 * Click event for when upload buttonin Action Column, it essentially runs the hiddenFileInput.click
 * @param event DOM event object for click
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Information pertinent to that column where this upload event is run from
 * @private
 */
function _uploadEvent(event, item, col) {
    try {
        event.stopPropagation();
    } catch (e) {
        window.event.cancelBubble = true;
    }
    this.dropzone.hiddenFileInput.click();
    this.dropzoneItemCache = item;
    this.updateFolder(null, item);
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
    if (item.data.provider === 'osfstorage') {
        item.data.extra.downloads++;
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
    item.notify.update('Deleting...', 'deleting', undefined, 3000);
    if (item.data.permissions.edit) {
        // delete from server, if successful delete from view
        $.ajax({
            url: waterbutler.buildTreeBeardDelete(item),
            type : 'DELETE'
        })
        .done(function(data) {
            // delete view
            tb.deleteNode(item.parentID, item.id);
            window.console.log('Delete success: ', data);
        })
        .fail(function(data){
            window.console.log('Delete failed: ', data);
            item.notify.update('Delete failed.', 'danger', undefined, 3000);
        });
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
function _fangornFileExists(item, file) {
    var i,
        child;
    for (i = 0; i < item.children.length; i++) {
        child = item.children[i];
        if (child.kind === 'item' && child.data.name === file.name) {
            return true;
        }
    }
    return false;
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
        item.notify.update('Files couldn\'t load, please try again later.', 'deleting', undefined, 3000);
    }
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
    //
    // Upload button if this is a folder
    if (item.kind === 'folder' && item.data.provider && item.data.permissions.edit) {
        buttons.push({
            'name' : '',
            'icon' : 'icon-upload-alt',
            'css' : 'fangorn-clickable btn btn-default btn-xs',
            'onclick' : _uploadEvent
        });
    }
    //Download button if this is an item
    if (item.kind === 'file') {
        buttons.push({
            'name' : '',
            'icon' : 'icon-download-alt',
            'css' : 'btn btn-info btn-xs',
            'onclick' : _downloadEvent
        }, {
            'name' : '',
            'icon' : 'icon-remove',
            'css' : 'm-l-lg text-danger fg-hover-hide',
            'style' : 'display:none',
            'onclick' : _removeEvent
        });
    }
    // Build the template for icons
    return buttons.map(function (btn) {
        return m('span', { 'data-col' : item.id }, [ m('i',
            { 'class' : btn.css, style : btn.style, 'onclick' : function(event) { btn.onclick.call(self, event, item, col); } },
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
    item.data.permissions = item.data.permissions || item.parent().data.permissions;
    return m('span',{
        onclick : function() {
            if (item.kind === 'file') {
                var params = $.param(
                    $.extend({
                        provider: item.data.provider,
                        path: item.data.path.substring(1)
                    },
                        item.data.extra || {}
                    )
                );
                window.location = nodeApiUrl + 'waterbutler/files/?' + params;
            }
        }
    }, item.data.name);
}

/**
 * Parent function for resolving rows, all columns are sub methods within this function
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {Array} An array of columns that get iterated through in Treebeard
 * @private
 */
function _fangornResolveRows(item) {
    var default_columns = [],
        checkConfig = false,
        configOption;

    item.css = '';

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
        width : '50%',
        sort : true,
        sortType : 'text'
    }, {
        title : 'Actions',
        width : '25%',
        sort : false
    }, {
        title : 'Downloads',
        width : '25%',
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
    showFilter : true,     // Gives the option to filter by showing the filter box.
    filterStyle : { 'float' : 'right', 'width' : '50%'},
    title : false,          // Title of the grid, boolean, string OR function that returns a string.
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
    },
    createcheck : function (item, parent) {
        window.console.log('createcheck', this, item, parent);
        return true;
    },
    deletecheck : function (item) {  // When user attempts to delete a row, allows for checking permissions etc.
        window.console.log('deletecheck', this, item);
        return true;
    },
    movecheck : function (to, from) { //This method gives the users an option to do checks and define their return
        window.console.log('movecheck: to', to, 'from', from);
        return true;
    },
    movefail : function (to, from) { //This method gives the users an option to do checks and define their return
        window.console.log('moovefail: to', to, 'from', from);
        return true;
    },
    addcheck : function (treebeard, item, file) {
        var size,
            maxSize,
            msgText;
        if (item.data.provider && item.kind === 'folder') {
            if (item.data.permissions.edit) {
                if (!_fangornFileExists.call(treebeard, item, file)) {
                    if (item.data.accept && item.data.accept.maxSize) {
                        size = Math.round(file.size / 10000) / 100;
                        maxSize = item.data.accept.maxSize;
                        if (maxSize >= size && file.size > 0) {
                            return true;
                        }
                        if (maxSize < size) {
                            msgText = 'One of the files is too large (' + size + ' MB). Max file size is ' + item.data.accept.maxSize + ' MB.';
                            item.notify.update(msgText, 'warning', undefined, 3000);
                        }
                        if (size === 0) {
                            msgText = 'Some files were ignored because they were empty.';
                            item.notify.update(msgText, 'warning', undefined, 3000);
                        }
                        return false;
                    }
                    return true;
                }
                msgText = 'File already exists.';
                item.notify.update(msgText, 'warning', 1, 3000);
            } else {
                msgText = 'You don\'t have permission to upload here';
                item.notify.update(msgText, 'warning', 1, 3000, 'animated flipInX');
            }
        }

        return false;
    },
    onselectrow : function (item) {
        window.console.log('Row: ', item);
    },
    onmouseoverrow : _fangornMouseOverRow,
    dropzone : {                                           // All dropzone options.
        url: function(files) {return files[0].url;},
        clickable : '#treeGrid',
        addRemoveLinks: false,
        previewTemplate: '<div></div>',
        parallelUploads: 1
    },
    resolveIcon : _fangornResolveIcon,
    resolveToggle : _fangornResolveToggle,
    // Pass ``null`` to avoid overwriting Dropzone URL resolver
    resolveUploadUrl: function() {return null;},
    resolveLazyloadUrl : _fangornResolveLazyLoad,
    resolveUploadMethod: _fangornUploadMethod,
    lazyLoadError : _fangornLazyLoadError,
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
    },
};

Fangorn.ButtonEvents = {
    _downloadEvent: _downloadEvent,
    _uploadEvent: _uploadEvent,
    _removeEvent: _removeEvent
};

module.exports = Fangorn;

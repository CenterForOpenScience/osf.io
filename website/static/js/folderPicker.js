/**
 * A simple folder picker plugin built on HGrid.
 * Takes the same options as HGrid and additionally requires an
 * `onChooseFolder` option (the callback executed when a folder is selected).
 *
 * Usage:
 *
 *     $('#myPicker').folderpicker({
 *         data: // Array of HGrid-formatted data or URL to fetch data
 *         onPickFolder: function(evt, folder) {
 *             // do something with folder
 *         }
 *     });
 */
'use strict';
var ko = require('knockout');
var kom = require('knockout-mapping');
require('knockout-punches');
var m = require('mithril');
var Treebeard = require('treebeard');
var $ = require('jquery');
var $osf = require('osfHelpers');

ko.punches.enableAll();

function _treebeardToggleCheck(item) {
    if (item.data.addon === 'figshare') {
        return false;
    }

    if (item.data.path === '/') {
        return false;
    }
    return true;
}

function _treebeardResolveToggle(item) {
    if (item.data.addon === 'figshare') {
        return '';
    }

    if (item.data.path !== '/') {
        var toggleMinus = m('i.icon-minus', ' '),
            togglePlus = m('i.icon-plus', ' ');
        if (item.kind === 'folder') {
            if (item.open) {
                return toggleMinus;
            }
            return togglePlus;
        }
    }
    item.open = true;
    return '';
}

// Returns custom icons for OSF
function _treebeardResolveIcon(item) {
    var openFolder = m('i.icon-folder-open-alt', ' '),
        closedFolder = m('i.icon-folder-close-alt', ' ');

    if (item.open) {
        return openFolder;
    }

    return closedFolder;
}

var INPUT_NAME = '-folder-select';
//THIS NEEDS TO BE FIXED SO THAT ON CLICK IT OPENS THE FOLDER.
function _treebeardTitleColumn(item, col) {
    return m('span', item.data.name);
}

/**
 * Returns the folder select button for a single row.
 */
function _treebeardSelectView(item) {
    var tb = this;
    var setTempPicked = function() {
        this._tempPicked = item.data.path;
    };
    var templateChecked = m('input', {
        type: 'radio',
        checked: 'checked',
        name: '#' + tb.options.divID + INPUT_NAME,
        value: item.id
    }, ' ');
    var templateUnchecked = m('input', {
        type: 'radio',
        onclick: setTempPicked.bind(tb),
        name: '#' + tb.options.divID + INPUT_NAME,
        value: item.id
    }, ' ');

    if (tb._tempPicked) {
        if (tb._tempPicked === item.data.path) {
            return templateChecked;
        } else {
            return templateUnchecked;
        }
    }

    if (item.data.path != undefined) {
        if (item.data.path === tb.options.folderPath) {
            return templateChecked;
        }
    }

    if (tb.options.folderArray && item.data.name === tb.options.folderArray[0]) {
        return templateChecked;
    }

    return templateUnchecked;
}

function _treebeardColumnTitle() {
    var columns = [];
    columns.push({
        title: 'Folders',
        width: '75%',
        sort: false
    }, {
        title: 'Select',
        width: '25%',
        sort: false
    });

    return columns;
}

function _treebeardResolveRows(item) {
    // this = treebeard;
    item.css = '';
    var default_columns = []; // Defines columns based on data
    default_columns.push({
        data: 'name', // Data field name
        folderIcons: true,
        filter: false,
        custom: _treebeardTitleColumn
    });

    default_columns.push({
        sortInclude: false,
        css: 'p-l-xs',
        custom: _treebeardSelectView
    });

    return default_columns;

}

function _treebeardOnload() {
    var tb = this;
    var folderName = tb.options.initialFolderName;
    var folderPath = tb.options.initialFolderPath;
    var folderArray;
    if (folderName != undefined) {
        if (folderName === "None") {
            tb.options.folderPath = null;
        } else {
            if (folderPath) {
                tb.options.folderPath = folderName.replace(folderPath, ''); 
            }
            folderArray = folderName.trim().split('/');
            if (folderArray[folderArray.length - 1] === "") {
                folderArray.pop();
            }
            if (folderArray[0] === folderPath) {
                folderArray.shift();
            }
            tb.options.folderArray = folderArray;
        }
        for (var i = 0; i < tb.treeData.children.length; i++) {
            if (tb.treeData.children[i].data.addon !== 'figshare' && tb.treeData.children[i].data.name === folderArray[0]) {
                tb.updateFolder(null, tb.treeData.children[i]);
            }
        }
        tb.options.folderIndex = 1;
    }
    tb.options.folderPickerOnload();
}

function _treebeardLazyLoadOnLoad(item) {
    var tb = this;

    for (var i = 0; i < item.children.length; i++) {
        if (item.children[i].data.addon === 'figshare') {
            return;
        }
        if (item.children[i].data.name === tb.options.folderArray[tb.options.folderIndex]) {
            tb.updateFolder(null, item.children[i]);
            tb.options.folderIndex++;
            return;
        }
    }
}

// Default Treebeard options
var defaults = {
    columnTitles: _treebeardColumnTitle,
    resolveRows: _treebeardResolveRows,
    resolveIcon: _treebeardResolveIcon,
    togglecheck: _treebeardToggleCheck,
    resolveToggle: _treebeardResolveToggle,
    ondataload: _treebeardOnload,
    lazyLoadOnLoad: _treebeardLazyLoadOnLoad,
    // Disable uploads
    uploads: false,
    showFilter: false,
    resizeColumns: false,
    rowHeight: 35
};

function FolderPickerViewModel(name, url, selector, folderPicker, opts) {
    var self = this;
    self.selector = selector;
    // Auth information
    self.nodeHasAuth = ko.observable(false);
    // whether current user is authorizer of the addon
    self.userIsOwner = ko.observable(false);
    // whether current user has an auth token
    self.userHasAuth = ko.observable(false);
    // whether the auth token is valid
    self.validCredentials = ko.observable(true);
    // Currently linked folder, an Object of the form {name: ..., path: ...}
    self.folder = ko.observable({
        name: null,
        path: null
    });
    //
    self.ownerName = ko.observable('');
    self.urls = ko.observable({});
    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');
    // Display names
    self.PICKER = 'picker';
    self.SHARE = 'share';
    // Current folder display
    self.currentDisplay = ko.observable(null);
    // CSS selector for the folder picker div
    self.folderPicker = folderPicker;
    // Currently selected folder, an Object of the form {name: ..., path: ...}
    self.selected = ko.observable(null);
    // Emails of contributors, can only be populated by activating the share dialog
    self.emails = ko.observableArray([]);
    self.loading = ko.observable(false);
    // Whether the initial data has been fetched form the server. Used for
    // error handling.
    self.loadedSettings = ko.observable(false);
    // Whether the contributor emails have been loaded from the server
    self.loadedEmails = ko.observable(false);
    // Whether the folders have been loaded from the server
    self.loadedFolders = ko.observable(false);
    // Display name for Addon
    self.properName = name.charAt(0).toUpperCase() + name.slice(1);

    self.unpackSettings = function(res) {
        return res.result;
    };
    self.lazyLoadPreprocess = function(res) {
        return res;
    };
    self.resolveLazyloadUrl = function(item) {
        return item.data.urls.folders;
    };
    self.resolveName = function(item) {
        return item.data.name;
    };
    self.resolvePath = function(item) {
        return item.data.path;
    };
    self.serialize = function() {
        return ko.toJS(self);
    };
    self.submitSuccessCallback = function(res){
	return {};
    };

    if (typeof opts !== 'undefined') {
        var keys = Object.keys(opts);
        for (var i = 0; i < keys.length; i++) {
            var key = keys[i];
            if (key === 'extraData') {
                for (var j = 0; j < opts[key].length; j++) {
                    self[opts[key][j]] = ko.observable(null);
                }
                continue;
            }
            if (typeof opts[key] === 'function') {
                self[key] = opts[key].bind(self);
            } else {
                self[key] = opts[key];
            }
        }
    }

    // List of contributor emails as a comma-separated values
    self.emailList = ko.computed(function() {
        return self.emails().join([', ']);
    });

    self.disableShare = ko.computed(function() {
        return !self.urls().share;
    });

    /**
     * Update the view model from data returned from the server.
     */
    self.updateFromData = function(data) {
        // creates observables for the contents of data
        self.ownerName(data.ownerName);
        self.nodeHasAuth(data.nodeHasAuth);
        self.userIsOwner(data.userIsOwner);
        self.userHasAuth(data.userHasAuth);
        self.validCredentials(data.validCredentials);
        // Make sure folder has name and path properties defined
        self.folder(data.folder || {
            name: null,
            path: null
        });
        self.urls(data.urls);
	if (typeof opts['extraData'] !== 'undefined'){
	    for(var i = 0; i < opts['extraData'].length; i++){
		self[opts['extraData'][i]](data[opts['extraData'][i]]);
	    }
	}
    };

    self.fetchFromServer = function() {
        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                var data = self.unpackSettings(response);
                self.updateFromData(data);
                self.loadedSettings(true);
                if (!self.validCredentials()) {
                    if (self.userIsOwner()) {
                        self.changeMessage('Could not retrieve ' + self.properName + ' settings at ' +
                            'this time. The ' + self.properName + ' addon credentials may no longer be valid.' +
                            ' Try deauthorizing and reauthorizing ' + self.properName + ' on your <a href="' +
                            self.urls().settings + '">account settings page</a>.',
                            'text-warning');
                    } else {
                        self.changeMessage('Could not retrieve ' + self.properName + ' settings at ' +
                            'this time. The ' + self.properName + ' addon credentials may no longer be valid.' +
                            ' Contact ' + self.ownerName() + ' to verify.',
                            'text-warning');
                    }
                }
            },
            error: function(xhr, textStatus, error) {
                self.changeMessage('Could not retrieve ' + self.properName + ' settings at ' +
                    'this time. Please refresh ' +
                    'the page. If the problem persists, email ' +
                    '<a href="mailto:support@osf.io">support@osf.io</a>.',
                    'text-warning');
                Raven.captureMessage('Could not GET ' + self.properName + ' settings', {
                    url: url,
                    textStatus: textStatus,
                    error: error
                });
            }
        });
    };

    // Initial fetch from server
    self.fetchFromServer();

    self.toggleShare = function() {
        if (self.currentDisplay() === self.SHARE) {
            self.currentDisplay(null);
        } else {
            // Clear selection
            self.cancelSelection();
            self.currentDisplay(self.SHARE);
            self.activateShare();
        }
    };

    function onGetEmailsSuccess(response) {
        var emails = response.result.emails;
        self.emails(emails);
        self.loadedEmails(true);
    }

    self.activateShare = function() {
        if (!self.loadedEmails()) {
            $.ajax({
                url: self.urls().emails,
                type: 'GET',
                dataType: 'json',
                success: onGetEmailsSuccess
            });
        }
        var $copyBtn = $('#copyBtn');
        new ZeroClipboard($copyBtn);
    };


    /**
     * Whether or not to show the Import Access Token Button
     */
    self.showImport = ko.computed(function() {
        // Invoke the observables to ensure dependency tracking
        var userHasAuth = self.userHasAuth();
        var nodeHasAuth = self.nodeHasAuth();
        var loaded = self.loadedSettings();
        return userHasAuth && !nodeHasAuth && loaded;
    });

    /** Whether or not to show the full settings pane. */
    self.showSettings = ko.computed(function() {
        return self.nodeHasAuth();
    });

    /** Whether or not to show the Create Access Token button */
    self.showTokenCreateButton = ko.computed(function() {
        // Invoke the observables to ensure dependency tracking
        var userHasAuth = self.userHasAuth();
        var nodeHasAuth = self.nodeHasAuth();
        var loaded = self.loadedSettings();
        return !userHasAuth && !nodeHasAuth && loaded;
    });

    /** Computed functions for the linked and selected folders' display text.*/

    self.folderName = ko.computed(function() {
        // Invoke the observables to ensure dependency tracking
        var nodeHasAuth = self.nodeHasAuth();
        var folder = self.folder();
        return (nodeHasAuth && folder) ? folder.name : '';
    });

    self.selectedFolderName = ko.computed(function() {
        var userIsOwner = self.userIsOwner();
        var selected = self.selected();
        return (userIsOwner && selected) ? selected.name : '';
    });

    function onSubmitSuccess(response) {
        self.changeMessage('Successfully linked "' + self.selected().name +
            '". Go <a href="' + self.urls().files + '">here</a> to view your recently linked content.',
            'text-success', 5000);
        // Update folder in ViewModel
	self.sumbitSuccessCallback(response);
        self.cancelSelection();
    }

    function onSubmitError() {
        self.changeMessage('Could not change settings. Please try again later.', 'text-danger');
    }

    /**
     * Send a PUT request to change the linked content
     */
    self.submitSettings = function() {
        $osf.putJSON(self.urls().config, self.serialize())
            .done(onSubmitSuccess)
            .fail(onSubmitError);
    };

    /**
     * Must be used to update radio buttons and knockout view model simultaneously
     */
    self.cancelSelection = function() {
        self.selected(null);
    };

    /** Change the flashed message. */
    self.changeMessage = function(text, css, timeout) {
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    };

    /**
     * Send DELETE request to deauthorize this node.
     */
    function sendDeauth() {
        return $.ajax({
            url: self.urls().deauthorize,
            type: 'DELETE',
            success: function() {
                // Update observables
                self.nodeHasAuth(false);
                self.cancelSelection();
                self.currentDisplay(null);
                self.changeMessage('Deauthorized ' + self.properName + '.', 'text-warning', 3000);
            },
            error: function() {
                self.changeMessage('Could not deauthorize because of an error. Please try again later.',
                    'text-danger');
            }
        });
    }

    /** Pop up a confirmation to deauthorize this node.
     *  Send DELETE request if confirmed.
     */
    self.deauthorize = function() {
        bootbox.confirm({
            title: 'Deauthorize ' + self.properName + '?',
            message: 'Are you sure you want to remove this ' + self.properName + ' authorization?',
            callback: function(confirmed) {
                if (confirmed) {
                    return sendDeauth();
                }
            }
        });
    };

    // Callback for when PUT request to import user access token
    function onImportSuccess(response) {
        var msg = response.message || 'Successfully imported access token from profile.';
        // Update view model based on response
        self.changeMessage(msg, 'text-success', 3000);
        self.updateFromData(response.result);
        self.activatePicker();
    }

    function onImportError() {
        self.message('Error occurred while importing access token.');
        self.messageClass('text-danger');
    }

    /**
     * Send PUT request to import access token from user profile.
     */
    self.importAuth = function() {
        bootbox.confirm({
            title: 'Import ' + self.properName + ' Access Token?',
            message: 'Are you sure you want to authorize this project with your ' + self.properName + ' access token?',
            callback: function(confirmed) {
                if (confirmed) {
                    return $osf.putJSON(self.urls().importAuth, {})
                        .done(onImportSuccess)
                        .fail(onImportError);
                }
            }
        });
    };

    self.connectExistingAccount = function(account_id) {
        $osf.postJSON(
            self.urls().importAuth, {
                external_account_id: account_id
            }
        ).then(onImportSuccess, onImportError);
    };


    /** Callback for chooseFolder action.
     *   Just changes the ViewModel's self.selected observable to the selected
     *   folder.
     */
    function onPickFolder(evt, item) {
        evt.preventDefault();
        self.selected({
            name: self.resolveName(item),
            path: self.resolvePath(item),
            id: self.resolveId(item)
        });
        return false; // Prevent event propagation
    }

    /**
     * Activates the HGrid folder picker.
     */
    self.activatePicker = function() {
        self.currentDisplay(self.PICKER);
        // Only load folders if they haven't already been requested
        if (!self.loadedFolders()) {
            // Show loading indicator
            self.loading(true);
            $(self.folderPicker).folderpicker({
                onPickFolder: onPickFolder,
                initialFolderName: self.folderName(),
                initialFolderPath: self.properName,
                // Fetch folders with AJAX
                filesData: self.urls().folders, // URL for fetching folders
                // Lazy-load each folder's contents
                // Each row stores its url for fetching the folders it contains
                resolveLazyloadUrl: self.resolveLazyloadUrl,
                oddEvenClass: {
                    odd: 'addon-folderpicker-odd',
                    even: 'addon-folderpicker-even'
                },
                ajaxOptions: {
                    error: function(xhr, textStatus, error) {
                        self.loading(false);
                        self.changeMessage('Could not connect to ' + self.properName + ' at this time. ' +
                            'Please try again later.', 'text-warning');
                        Raven.captureMessage('Could not GET get ' + self.properName + ' contents.', {
                            textStatus: textStatus,
                            error: error
                        });
                    }
                },
                folderPickerOnload: function() {
                    // Hide loading indicator
                    self.loading(false);
                    // Set flag to prevent repeated requests
                    self.loadedFolders(true);
                },
                lazyLoadPreprocess: self.lazyLoadPreprocess
            });
        }
    };
    /**
     * Toggles the visibility of the folder picker.
     */
    self.togglePicker = function() {
        // Toggle visibility of folder picker
        var shown = self.currentDisplay() === self.PICKER;
        if (!shown) {
            self.currentDisplay(self.PICKER);
            self.activatePicker();
        } else {
            self.currentDisplay(null);
            // Clear selection
            self.cancelSelection();
        }
    };
}

function FolderPicker(selector, opts) {
    var self = this;
    self.selector = selector;
    self.checkedRowId = null;
    // Custom Treebeard action to select a folder that uses the passed in
    // "onChooseFolder" callback
    if (!opts.onPickFolder) {
        throw 'FolderPicker must have the "onPickFolder" option defined';
    }
    self.options = $.extend({}, defaults, opts);
    self.options.divID = selector.substring(1);
    self.options.initialFolderName = opts.initialFolderName;
    self.options.initialFolderPath = opts.initialFolderPath;

    // Start up the grid
    self.grid = new Treebeard(self.options).tbController;
    // Set up listener for folder selection

    $(selector).on('change', 'input[name="' + self.selector + INPUT_NAME + '"]', function(evt) {
        var id = $(this).val();
        var row = self.grid.find(id);

        //// Store checked state of rows so that it doesn't uncheck when HGrid is redrawn
        self.options.onPickFolder.call(self, evt, row);
    });
}

// Augment jQuery
$.fn.folderpicker = function(options) {
    this.each(function() {
        // Treebeard must take an ID as a selector if using as a jQuery plugin
        if (!this.id) {
            throw 'FolderPicker must have an ID if initializing with jQuery.';
        }
        var selector = '#' + this.id;
        return new FolderPicker(selector, options);
    });
};

module.exports = FolderPickerViewModel;

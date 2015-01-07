webpackJsonp([38],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

	var DropboxNodeConfig = __webpack_require__(46);

	var url = window.contextVars.node.urls.api + 'dropbox/config/';
	new DropboxNodeConfig('#dropboxScope', url, '#myDropboxGrid');


/***/ },

/***/ 46:
/***/ function(module, exports, __webpack_require__) {

	/**
	* Module that controls the Dropbox node settings. Includes Knockout view-model
	* for syncing data, and HGrid-folderpicker for selecting a folder.
	*/
	'use strict';

	var ko = __webpack_require__(16);
	__webpack_require__(7);
	var $ = __webpack_require__(14);
	var bootbox = __webpack_require__(11);
	var Raven = __webpack_require__(15);

	var FolderPicker = __webpack_require__(75);
	var ZeroClipboard = __webpack_require__(78);
	ZeroClipboard.config('/static/vendor/bower_components/zeroclipboard/dist/ZeroClipboard.swf');
	var $osf = __webpack_require__(2);

	ko.punches.enableAll();
	/**
	    * Knockout view model for the Dropbox node settings widget.
	    */
	var ViewModel = function(url, selector, folderPicker) {
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
	    self.folder = ko.observable({name: null, path: null});
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

	    // Whether the dropbox folders have been loaded from the server/Dropbox API
	    self.loadedFolders = ko.observable(false);

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
	        self.ownerName(data.ownerName);
	        self.nodeHasAuth(data.nodeHasAuth);
	        self.userIsOwner(data.userIsOwner);
	        self.userHasAuth(data.userHasAuth);
	        self.validCredentials(data.validCredentials);
	        // Make sure folder has name and path properties defined
	        self.folder(data.folder || {name: null, path: null});
	        self.urls(data.urls);
	    };

	    self.fetchFromServer = function() {
	        $.ajax({
	            url: url, type: 'GET', dataType: 'json',
	            success: function(response) {
	                self.updateFromData(response.result);
	                self.loadedSettings(true);
	                if (!self.validCredentials()){
	                    if (self.userIsOwner()) {
	                        self.changeMessage('Could not retrieve Dropbox settings at ' +
	                        'this time. The Dropbox addon credentials may no longer be valid.' +
	                        ' Try deauthorizing and reauthorizing Dropbox on your <a href="' +
	                            self.urls().settings + '">account settings page</a>.',
	                        'text-warning');
	                    } else {
	                        self.changeMessage('Could not retrieve Dropbox settings at ' +
	                        'this time. The Dropbox addon credentials may no longer be valid.' +
	                        ' Contact ' + self.ownerName() + ' to verify.',
	                        'text-warning');
	                    }
	                }
	            },
	            error: function(xhr, textStatus, error) {
	                self.changeMessage('Could not retrieve Dropbox settings at ' +
	                    'this time. Please refresh ' +
	                    'the page. If the problem persists, email ' +
	                    '<a href="mailto:support@osf.io">support@osf.io</a>.',
	                    'text-warning');
	                Raven.captureMessage('Could not GET Dropbox settings', {
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
	                url: self.urls().emails, type: 'GET', dataType: 'json',
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
	            '". Go to the <a href="' +
	            self.urls().files + '">Files page</a> to view your files.',
	            'text-success', 5000);
	        // Update folder in ViewModel
	        self.folder(response.result.folder);
	        self.urls(response.result.urls);
	        self.cancelSelection();
	    }

	    function onSubmitError() {
	        self.changeMessage('Could not change settings. Please try again later.', 'text-danger');
	    }

	    /**
	        * Send a PUT request to change the linked Dropbox folder.
	        */
	    self.submitSettings = function() {
	        $osf.putJSON(self.urls().config, ko.toJS(self))
	            .done(onSubmitSuccess)
	            .fail(onSubmitError);
	    };

	    /**
	        * Must be used to update radio buttons and knockout view model simultaneously
	        */
	    self.cancelSelection = function() {
	        self.selected(null);
	        // $(selector + ' input[type="radio"]').prop('checked', false);
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
	                self.changeMessage('Deauthorized Dropbox.', 'text-warning', 3000);
	            },
	            error: function() {
	                self.changeMessage('Could not deauthorize because of an error. Please try again later.',
	                    'text-danger');
	            }
	        });
	    }

	    /** Pop up a confirmation to deauthorize Dropbox from this node.
	        *  Send DELETE request if confirmed.
	        */
	    self.deauthorize = function() {
	        bootbox.confirm({
	            title: 'Deauthorize Dropbox?',
	            message: 'Are you sure you want to remove this Dropbox authorization?',
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
	            title: 'Import Dropbox Access Token?',
	            message: 'Are you sure you want to authorize this project with your Dropbox access token?',
	            callback: function(confirmed) {
	                if (confirmed) {
	                    return $osf.putJSON(self.urls().importAuth, {})
	                        .done(onImportSuccess)
	                        .fail(onImportError);
	                }
	            }
	        });
	    };

	    /** Callback for chooseFolder action.
	    *   Just changes the ViewModel's self.selected observable to the selected
	    *   folder.
	    */
	    function onPickFolder(evt, item) {
	            evt.preventDefault();
	            self.selected({name: 'Dropbox' + item.data.path, path: item.data.path});
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
	                initialFolderName : self.folderName(),
	                initialFolderPath : 'Dropbox',
	                // Fetch Dropbox folders with AJAX
	                filesData: self.urls().folders, // URL for fetching folders
	                // Lazy-load each folder's contents
	                // Each row stores its url for fetching the folders it contains

	                resolveLazyloadUrl : function(item){
	                    return item.data.urls.folders;
	                },
	                oddEvenClass : {
	                    odd : 'dropbox-folderpicker-odd',
	                    even : 'dropbox-folderpicker-even'
	                },
	                ajaxOptions: {
	                    error: function(xhr, textStatus, error) {
	                        self.loading(false);
	                        self.changeMessage('Could not connect to Dropbox at this time. ' +
	                                            'Please try again later.', 'text-warning');
	                        Raven.captureMessage('Could not GET get Dropbox contents.', {
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
	                }
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
	};

	// Public API
	function DropboxNodeConfig(selector, url, folderPicker) {
	    var self = this;
	    self.url = url;
	    self.folderPicker = folderPicker;
	    self.viewModel = new ViewModel(url, selector, folderPicker);
	    $osf.applyBindings(self.viewModel, selector);
	}

	module.exports = DropboxNodeConfig;


/***/ },

/***/ 75:
/***/ function(module, exports, __webpack_require__) {

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
	    var m = __webpack_require__(13);
	    var Treebeard = __webpack_require__(17);
	    var $ = __webpack_require__(14);

	    function _treebeardToggleCheck (item) {
	        if(item.data.addon === 'figshare') {
	            return false; 
	        }

	        if (item.data.path == "/") {
	            return false;
	        }
	        return true;
	    }

	    function _treebeardResolveToggle(item){
	        if(item.data.addon === 'figshare') {
	            return ''; 
	        }

	        if (item.data.path!="/") {
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
	    function _treebeardResolveIcon(item){
	        var openFolder  = m('i.icon-folder-open-alt', ' '),
	            closedFolder = m('i.icon-folder-close-alt', ' ');

	        if (item.open) {
	            return openFolder;
	        }

	        return closedFolder;
	    }

	    var INPUT_NAME = '-folder-select';
	    //THIS NEEDS TO BE FIXED SO THAT ON CLICK IT OPENS THE FOLDER.
	    function _treebeardTitleColumn (item, col) {
	        return m('span', item.data.name);
	    }

	    /**
	     * Returns the folder select button for a single row.
	     */
	    function _treebeardSelectView(item) {

	        if(item.data.path != undefined){
	            if (item.data.path === this.options.folderPath) {
	                return m("input",{
	                type:"radio",
	                checked : 'checked',
	                name: "#" + this.options.divID + INPUT_NAME,
	                value:item.id
	                }, " ");
	            }
	        }

	        if (this.options.folderArray && item.data.name === this.options.folderArray[0]) {
	            return m("input",{
	                type:"radio",
	                checked : 'checked',
	                name: "#" + this.options.divID + INPUT_NAME,
	                value:item.id
	                }, " ");
	        }

	        return m("input",{
	            type:"radio",
	            name: "#" + this.options.divID + INPUT_NAME,
	            value:item.id
	        }, " ");
	    }

	    function _treebeardColumnTitle(){
	        var columns = [];
	        columns.push({
	            title: 'Folders',
	            width : '75%',
	            sort : false
	        },
	        {
	            title : 'Select',
	            width : '25%',
	            sort : false
	        });

	        return columns;
	    }

	    function _treebeardResolveRows(item){
	        // this = treebeard;
	        item.css = '';
	        var default_columns = [];             // Defines columns based on data
	        default_columns.push({
	            data : 'name',  // Data field name
	            folderIcons : true,
	            filter : false,
	            custom : _treebeardTitleColumn
	        });

	        default_columns.push(
	            {
	            sortInclude : false,
	            css : 'p-l-xs',
	            custom : _treebeardSelectView
	        });

	        return default_columns;

	    }

	    function _treebeardOnload () {
	        var tb = this;
	        var folderName = tb.options.initialFolderName;
	        var folderPath = tb.options.initialFolderPath;
	        if (folderName != undefined) {
	            if (folderName === "None") {
	                tb.options.folderPath = null;
	            } else {
	                if(folderPath) {
	                    tb.options.folderPath = folderName.replace(folderPath, '');  //folderName.replace('Dropbox', '');
	                }
	                var folderArray = folderName.trim().split('/');
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

	    function _treebeardLazyLoadOnLoad  (item) {
	        var tb = this; 
	        for (var i = 0; i < item.children.length; i++) {
	            if (item.children[i].data.addon === 'figshare'){
	                return;
	            }
	            if (item.children[i].data.name === tb.options.folderArray[tb.options.folderIndex]) {
	                tb.updateFolder(null,item.children[i]);
	                tb.options.folderIndex++; 
	                return; 
	            }
	        }
	    }

	    // Default Treebeard options
	    var defaults = {
	        columnTitles : _treebeardColumnTitle,
	        resolveRows : _treebeardResolveRows,
	        resolveIcon : _treebeardResolveIcon,
	        togglecheck : _treebeardToggleCheck,
	        resolveToggle : _treebeardResolveToggle,
	        onload : _treebeardOnload,
	        lazyLoadOnLoad : _treebeardLazyLoadOnLoad,
	        // Disable uploads
	        uploads: false,
	        showFilter : false,
	        resizeColumns : false
	    };

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
	            if (!this.id) { throw 'FolderPicker must have an ID if initializing with jQuery.'; }
	            var selector = '#' + this.id;
	            return new FolderPicker(selector, options);
	        });
	    };
	 
	module.exports = FolderPicker;


/***/ },

/***/ 78:
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function(module) {/*!
	 * ZeroClipboard
	 * The ZeroClipboard library provides an easy way to copy text to the clipboard using an invisible Adobe Flash movie and a JavaScript interface.
	 * Copyright (c) 2014 Jon Rohan, James M. Greene
	 * Licensed MIT
	 * http://zeroclipboard.org/
	 * v2.1.6
	 */
	(function(window, undefined) {
	  "use strict";
	  /**
	 * Store references to critically important global functions that may be
	 * overridden on certain web pages.
	 */
	  var _window = window, _document = _window.document, _navigator = _window.navigator, _setTimeout = _window.setTimeout, _encodeURIComponent = _window.encodeURIComponent, _ActiveXObject = _window.ActiveXObject, _Error = _window.Error, _parseInt = _window.Number.parseInt || _window.parseInt, _parseFloat = _window.Number.parseFloat || _window.parseFloat, _isNaN = _window.Number.isNaN || _window.isNaN, _round = _window.Math.round, _now = _window.Date.now, _keys = _window.Object.keys, _defineProperty = _window.Object.defineProperty, _hasOwn = _window.Object.prototype.hasOwnProperty, _slice = _window.Array.prototype.slice, _unwrap = function() {
	    var unwrapper = function(el) {
	      return el;
	    };
	    if (typeof _window.wrap === "function" && typeof _window.unwrap === "function") {
	      try {
	        var div = _document.createElement("div");
	        var unwrappedDiv = _window.unwrap(div);
	        if (div.nodeType === 1 && unwrappedDiv && unwrappedDiv.nodeType === 1) {
	          unwrapper = _window.unwrap;
	        }
	      } catch (e) {}
	    }
	    return unwrapper;
	  }();
	  /**
	 * Convert an `arguments` object into an Array.
	 *
	 * @returns The arguments as an Array
	 * @private
	 */
	  var _args = function(argumentsObj) {
	    return _slice.call(argumentsObj, 0);
	  };
	  /**
	 * Shallow-copy the owned, enumerable properties of one object over to another, similar to jQuery's `$.extend`.
	 *
	 * @returns The target object, augmented
	 * @private
	 */
	  var _extend = function() {
	    var i, len, arg, prop, src, copy, args = _args(arguments), target = args[0] || {};
	    for (i = 1, len = args.length; i < len; i++) {
	      if ((arg = args[i]) != null) {
	        for (prop in arg) {
	          if (_hasOwn.call(arg, prop)) {
	            src = target[prop];
	            copy = arg[prop];
	            if (target !== copy && copy !== undefined) {
	              target[prop] = copy;
	            }
	          }
	        }
	      }
	    }
	    return target;
	  };
	  /**
	 * Return a deep copy of the source object or array.
	 *
	 * @returns Object or Array
	 * @private
	 */
	  var _deepCopy = function(source) {
	    var copy, i, len, prop;
	    if (typeof source !== "object" || source == null) {
	      copy = source;
	    } else if (typeof source.length === "number") {
	      copy = [];
	      for (i = 0, len = source.length; i < len; i++) {
	        if (_hasOwn.call(source, i)) {
	          copy[i] = _deepCopy(source[i]);
	        }
	      }
	    } else {
	      copy = {};
	      for (prop in source) {
	        if (_hasOwn.call(source, prop)) {
	          copy[prop] = _deepCopy(source[prop]);
	        }
	      }
	    }
	    return copy;
	  };
	  /**
	 * Makes a shallow copy of `obj` (like `_extend`) but filters its properties based on a list of `keys` to keep.
	 * The inverse of `_omit`, mostly. The big difference is that these properties do NOT need to be enumerable to
	 * be kept.
	 *
	 * @returns A new filtered object.
	 * @private
	 */
	  var _pick = function(obj, keys) {
	    var newObj = {};
	    for (var i = 0, len = keys.length; i < len; i++) {
	      if (keys[i] in obj) {
	        newObj[keys[i]] = obj[keys[i]];
	      }
	    }
	    return newObj;
	  };
	  /**
	 * Makes a shallow copy of `obj` (like `_extend`) but filters its properties based on a list of `keys` to omit.
	 * The inverse of `_pick`.
	 *
	 * @returns A new filtered object.
	 * @private
	 */
	  var _omit = function(obj, keys) {
	    var newObj = {};
	    for (var prop in obj) {
	      if (keys.indexOf(prop) === -1) {
	        newObj[prop] = obj[prop];
	      }
	    }
	    return newObj;
	  };
	  /**
	 * Remove all owned, enumerable properties from an object.
	 *
	 * @returns The original object without its owned, enumerable properties.
	 * @private
	 */
	  var _deleteOwnProperties = function(obj) {
	    if (obj) {
	      for (var prop in obj) {
	        if (_hasOwn.call(obj, prop)) {
	          delete obj[prop];
	        }
	      }
	    }
	    return obj;
	  };
	  /**
	 * Determine if an element is contained within another element.
	 *
	 * @returns Boolean
	 * @private
	 */
	  var _containedBy = function(el, ancestorEl) {
	    if (el && el.nodeType === 1 && el.ownerDocument && ancestorEl && (ancestorEl.nodeType === 1 && ancestorEl.ownerDocument && ancestorEl.ownerDocument === el.ownerDocument || ancestorEl.nodeType === 9 && !ancestorEl.ownerDocument && ancestorEl === el.ownerDocument)) {
	      do {
	        if (el === ancestorEl) {
	          return true;
	        }
	        el = el.parentNode;
	      } while (el);
	    }
	    return false;
	  };
	  /**
	 * Get the URL path's parent directory.
	 *
	 * @returns String or `undefined`
	 * @private
	 */
	  var _getDirPathOfUrl = function(url) {
	    var dir;
	    if (typeof url === "string" && url) {
	      dir = url.split("#")[0].split("?")[0];
	      dir = url.slice(0, url.lastIndexOf("/") + 1);
	    }
	    return dir;
	  };
	  /**
	 * Get the current script's URL by throwing an `Error` and analyzing it.
	 *
	 * @returns String or `undefined`
	 * @private
	 */
	  var _getCurrentScriptUrlFromErrorStack = function(stack) {
	    var url, matches;
	    if (typeof stack === "string" && stack) {
	      matches = stack.match(/^(?:|[^:@]*@|.+\)@(?=http[s]?|file)|.+?\s+(?: at |@)(?:[^:\(]+ )*[\(]?)((?:http[s]?|file):\/\/[\/]?.+?\/[^:\)]*?)(?::\d+)(?::\d+)?/);
	      if (matches && matches[1]) {
	        url = matches[1];
	      } else {
	        matches = stack.match(/\)@((?:http[s]?|file):\/\/[\/]?.+?\/[^:\)]*?)(?::\d+)(?::\d+)?/);
	        if (matches && matches[1]) {
	          url = matches[1];
	        }
	      }
	    }
	    return url;
	  };
	  /**
	 * Get the current script's URL by throwing an `Error` and analyzing it.
	 *
	 * @returns String or `undefined`
	 * @private
	 */
	  var _getCurrentScriptUrlFromError = function() {
	    var url, err;
	    try {
	      throw new _Error();
	    } catch (e) {
	      err = e;
	    }
	    if (err) {
	      url = err.sourceURL || err.fileName || _getCurrentScriptUrlFromErrorStack(err.stack);
	    }
	    return url;
	  };
	  /**
	 * Get the current script's URL.
	 *
	 * @returns String or `undefined`
	 * @private
	 */
	  var _getCurrentScriptUrl = function() {
	    var jsPath, scripts, i;
	    if (_document.currentScript && (jsPath = _document.currentScript.src)) {
	      return jsPath;
	    }
	    scripts = _document.getElementsByTagName("script");
	    if (scripts.length === 1) {
	      return scripts[0].src || undefined;
	    }
	    if ("readyState" in scripts[0]) {
	      for (i = scripts.length; i--; ) {
	        if (scripts[i].readyState === "interactive" && (jsPath = scripts[i].src)) {
	          return jsPath;
	        }
	      }
	    }
	    if (_document.readyState === "loading" && (jsPath = scripts[scripts.length - 1].src)) {
	      return jsPath;
	    }
	    if (jsPath = _getCurrentScriptUrlFromError()) {
	      return jsPath;
	    }
	    return undefined;
	  };
	  /**
	 * Get the unanimous parent directory of ALL script tags.
	 * If any script tags are either (a) inline or (b) from differing parent
	 * directories, this method must return `undefined`.
	 *
	 * @returns String or `undefined`
	 * @private
	 */
	  var _getUnanimousScriptParentDir = function() {
	    var i, jsDir, jsPath, scripts = _document.getElementsByTagName("script");
	    for (i = scripts.length; i--; ) {
	      if (!(jsPath = scripts[i].src)) {
	        jsDir = null;
	        break;
	      }
	      jsPath = _getDirPathOfUrl(jsPath);
	      if (jsDir == null) {
	        jsDir = jsPath;
	      } else if (jsDir !== jsPath) {
	        jsDir = null;
	        break;
	      }
	    }
	    return jsDir || undefined;
	  };
	  /**
	 * Get the presumed location of the "ZeroClipboard.swf" file, based on the location
	 * of the executing JavaScript file (e.g. "ZeroClipboard.js", etc.).
	 *
	 * @returns String
	 * @private
	 */
	  var _getDefaultSwfPath = function() {
	    var jsDir = _getDirPathOfUrl(_getCurrentScriptUrl()) || _getUnanimousScriptParentDir() || "";
	    return jsDir + "ZeroClipboard.swf";
	  };
	  /**
	 * Keep track of the state of the Flash object.
	 * @private
	 */
	  var _flashState = {
	    bridge: null,
	    version: "0.0.0",
	    pluginType: "unknown",
	    disabled: null,
	    outdated: null,
	    unavailable: null,
	    deactivated: null,
	    overdue: null,
	    ready: null
	  };
	  /**
	 * The minimum Flash Player version required to use ZeroClipboard completely.
	 * @readonly
	 * @private
	 */
	  var _minimumFlashVersion = "11.0.0";
	  /**
	 * Keep track of all event listener registrations.
	 * @private
	 */
	  var _handlers = {};
	  /**
	 * Keep track of the currently activated element.
	 * @private
	 */
	  var _currentElement;
	  /**
	 * Keep track of the element that was activated when a `copy` process started.
	 * @private
	 */
	  var _copyTarget;
	  /**
	 * Keep track of data for the pending clipboard transaction.
	 * @private
	 */
	  var _clipData = {};
	  /**
	 * Keep track of data formats for the pending clipboard transaction.
	 * @private
	 */
	  var _clipDataFormatMap = null;
	  /**
	 * The `message` store for events
	 * @private
	 */
	  var _eventMessages = {
	    ready: "Flash communication is established",
	    error: {
	      "flash-disabled": "Flash is disabled or not installed",
	      "flash-outdated": "Flash is too outdated to support ZeroClipboard",
	      "flash-unavailable": "Flash is unable to communicate bidirectionally with JavaScript",
	      "flash-deactivated": "Flash is too outdated for your browser and/or is configured as click-to-activate",
	      "flash-overdue": "Flash communication was established but NOT within the acceptable time limit"
	    }
	  };
	  /**
	 * ZeroClipboard configuration defaults for the Core module.
	 * @private
	 */
	  var _globalConfig = {
	    swfPath: _getDefaultSwfPath(),
	    trustedDomains: window.location.host ? [ window.location.host ] : [],
	    cacheBust: true,
	    forceEnhancedClipboard: false,
	    flashLoadTimeout: 3e4,
	    autoActivate: true,
	    bubbleEvents: true,
	    containerId: "global-zeroclipboard-html-bridge",
	    containerClass: "global-zeroclipboard-container",
	    swfObjectId: "global-zeroclipboard-flash-bridge",
	    hoverClass: "zeroclipboard-is-hover",
	    activeClass: "zeroclipboard-is-active",
	    forceHandCursor: false,
	    title: null,
	    zIndex: 999999999
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.config`.
	 * @private
	 */
	  var _config = function(options) {
	    if (typeof options === "object" && options !== null) {
	      for (var prop in options) {
	        if (_hasOwn.call(options, prop)) {
	          if (/^(?:forceHandCursor|title|zIndex|bubbleEvents)$/.test(prop)) {
	            _globalConfig[prop] = options[prop];
	          } else if (_flashState.bridge == null) {
	            if (prop === "containerId" || prop === "swfObjectId") {
	              if (_isValidHtml4Id(options[prop])) {
	                _globalConfig[prop] = options[prop];
	              } else {
	                throw new Error("The specified `" + prop + "` value is not valid as an HTML4 Element ID");
	              }
	            } else {
	              _globalConfig[prop] = options[prop];
	            }
	          }
	        }
	      }
	    }
	    if (typeof options === "string" && options) {
	      if (_hasOwn.call(_globalConfig, options)) {
	        return _globalConfig[options];
	      }
	      return;
	    }
	    return _deepCopy(_globalConfig);
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.state`.
	 * @private
	 */
	  var _state = function() {
	    return {
	      browser: _pick(_navigator, [ "userAgent", "platform", "appName" ]),
	      flash: _omit(_flashState, [ "bridge" ]),
	      zeroclipboard: {
	        version: ZeroClipboard.version,
	        config: ZeroClipboard.config()
	      }
	    };
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.isFlashUnusable`.
	 * @private
	 */
	  var _isFlashUnusable = function() {
	    return !!(_flashState.disabled || _flashState.outdated || _flashState.unavailable || _flashState.deactivated);
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.on`.
	 * @private
	 */
	  var _on = function(eventType, listener) {
	    var i, len, events, added = {};
	    if (typeof eventType === "string" && eventType) {
	      events = eventType.toLowerCase().split(/\s+/);
	    } else if (typeof eventType === "object" && eventType && typeof listener === "undefined") {
	      for (i in eventType) {
	        if (_hasOwn.call(eventType, i) && typeof i === "string" && i && typeof eventType[i] === "function") {
	          ZeroClipboard.on(i, eventType[i]);
	        }
	      }
	    }
	    if (events && events.length) {
	      for (i = 0, len = events.length; i < len; i++) {
	        eventType = events[i].replace(/^on/, "");
	        added[eventType] = true;
	        if (!_handlers[eventType]) {
	          _handlers[eventType] = [];
	        }
	        _handlers[eventType].push(listener);
	      }
	      if (added.ready && _flashState.ready) {
	        ZeroClipboard.emit({
	          type: "ready"
	        });
	      }
	      if (added.error) {
	        var errorTypes = [ "disabled", "outdated", "unavailable", "deactivated", "overdue" ];
	        for (i = 0, len = errorTypes.length; i < len; i++) {
	          if (_flashState[errorTypes[i]] === true) {
	            ZeroClipboard.emit({
	              type: "error",
	              name: "flash-" + errorTypes[i]
	            });
	            break;
	          }
	        }
	      }
	    }
	    return ZeroClipboard;
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.off`.
	 * @private
	 */
	  var _off = function(eventType, listener) {
	    var i, len, foundIndex, events, perEventHandlers;
	    if (arguments.length === 0) {
	      events = _keys(_handlers);
	    } else if (typeof eventType === "string" && eventType) {
	      events = eventType.split(/\s+/);
	    } else if (typeof eventType === "object" && eventType && typeof listener === "undefined") {
	      for (i in eventType) {
	        if (_hasOwn.call(eventType, i) && typeof i === "string" && i && typeof eventType[i] === "function") {
	          ZeroClipboard.off(i, eventType[i]);
	        }
	      }
	    }
	    if (events && events.length) {
	      for (i = 0, len = events.length; i < len; i++) {
	        eventType = events[i].toLowerCase().replace(/^on/, "");
	        perEventHandlers = _handlers[eventType];
	        if (perEventHandlers && perEventHandlers.length) {
	          if (listener) {
	            foundIndex = perEventHandlers.indexOf(listener);
	            while (foundIndex !== -1) {
	              perEventHandlers.splice(foundIndex, 1);
	              foundIndex = perEventHandlers.indexOf(listener, foundIndex);
	            }
	          } else {
	            perEventHandlers.length = 0;
	          }
	        }
	      }
	    }
	    return ZeroClipboard;
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.handlers`.
	 * @private
	 */
	  var _listeners = function(eventType) {
	    var copy;
	    if (typeof eventType === "string" && eventType) {
	      copy = _deepCopy(_handlers[eventType]) || null;
	    } else {
	      copy = _deepCopy(_handlers);
	    }
	    return copy;
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.emit`.
	 * @private
	 */
	  var _emit = function(event) {
	    var eventCopy, returnVal, tmp;
	    event = _createEvent(event);
	    if (!event) {
	      return;
	    }
	    if (_preprocessEvent(event)) {
	      return;
	    }
	    if (event.type === "ready" && _flashState.overdue === true) {
	      return ZeroClipboard.emit({
	        type: "error",
	        name: "flash-overdue"
	      });
	    }
	    eventCopy = _extend({}, event);
	    _dispatchCallbacks.call(this, eventCopy);
	    if (event.type === "copy") {
	      tmp = _mapClipDataToFlash(_clipData);
	      returnVal = tmp.data;
	      _clipDataFormatMap = tmp.formatMap;
	    }
	    return returnVal;
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.create`.
	 * @private
	 */
	  var _create = function() {
	    if (typeof _flashState.ready !== "boolean") {
	      _flashState.ready = false;
	    }
	    if (!ZeroClipboard.isFlashUnusable() && _flashState.bridge === null) {
	      var maxWait = _globalConfig.flashLoadTimeout;
	      if (typeof maxWait === "number" && maxWait >= 0) {
	        _setTimeout(function() {
	          if (typeof _flashState.deactivated !== "boolean") {
	            _flashState.deactivated = true;
	          }
	          if (_flashState.deactivated === true) {
	            ZeroClipboard.emit({
	              type: "error",
	              name: "flash-deactivated"
	            });
	          }
	        }, maxWait);
	      }
	      _flashState.overdue = false;
	      _embedSwf();
	    }
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.destroy`.
	 * @private
	 */
	  var _destroy = function() {
	    ZeroClipboard.clearData();
	    ZeroClipboard.blur();
	    ZeroClipboard.emit("destroy");
	    _unembedSwf();
	    ZeroClipboard.off();
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.setData`.
	 * @private
	 */
	  var _setData = function(format, data) {
	    var dataObj;
	    if (typeof format === "object" && format && typeof data === "undefined") {
	      dataObj = format;
	      ZeroClipboard.clearData();
	    } else if (typeof format === "string" && format) {
	      dataObj = {};
	      dataObj[format] = data;
	    } else {
	      return;
	    }
	    for (var dataFormat in dataObj) {
	      if (typeof dataFormat === "string" && dataFormat && _hasOwn.call(dataObj, dataFormat) && typeof dataObj[dataFormat] === "string" && dataObj[dataFormat]) {
	        _clipData[dataFormat] = dataObj[dataFormat];
	      }
	    }
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.clearData`.
	 * @private
	 */
	  var _clearData = function(format) {
	    if (typeof format === "undefined") {
	      _deleteOwnProperties(_clipData);
	      _clipDataFormatMap = null;
	    } else if (typeof format === "string" && _hasOwn.call(_clipData, format)) {
	      delete _clipData[format];
	    }
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.getData`.
	 * @private
	 */
	  var _getData = function(format) {
	    if (typeof format === "undefined") {
	      return _deepCopy(_clipData);
	    } else if (typeof format === "string" && _hasOwn.call(_clipData, format)) {
	      return _clipData[format];
	    }
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.focus`/`ZeroClipboard.activate`.
	 * @private
	 */
	  var _focus = function(element) {
	    if (!(element && element.nodeType === 1)) {
	      return;
	    }
	    if (_currentElement) {
	      _removeClass(_currentElement, _globalConfig.activeClass);
	      if (_currentElement !== element) {
	        _removeClass(_currentElement, _globalConfig.hoverClass);
	      }
	    }
	    _currentElement = element;
	    _addClass(element, _globalConfig.hoverClass);
	    var newTitle = element.getAttribute("title") || _globalConfig.title;
	    if (typeof newTitle === "string" && newTitle) {
	      var htmlBridge = _getHtmlBridge(_flashState.bridge);
	      if (htmlBridge) {
	        htmlBridge.setAttribute("title", newTitle);
	      }
	    }
	    var useHandCursor = _globalConfig.forceHandCursor === true || _getStyle(element, "cursor") === "pointer";
	    _setHandCursor(useHandCursor);
	    _reposition();
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.blur`/`ZeroClipboard.deactivate`.
	 * @private
	 */
	  var _blur = function() {
	    var htmlBridge = _getHtmlBridge(_flashState.bridge);
	    if (htmlBridge) {
	      htmlBridge.removeAttribute("title");
	      htmlBridge.style.left = "0px";
	      htmlBridge.style.top = "-9999px";
	      htmlBridge.style.width = "1px";
	      htmlBridge.style.top = "1px";
	    }
	    if (_currentElement) {
	      _removeClass(_currentElement, _globalConfig.hoverClass);
	      _removeClass(_currentElement, _globalConfig.activeClass);
	      _currentElement = null;
	    }
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.activeElement`.
	 * @private
	 */
	  var _activeElement = function() {
	    return _currentElement || null;
	  };
	  /**
	 * Check if a value is a valid HTML4 `ID` or `Name` token.
	 * @private
	 */
	  var _isValidHtml4Id = function(id) {
	    return typeof id === "string" && id && /^[A-Za-z][A-Za-z0-9_:\-\.]*$/.test(id);
	  };
	  /**
	 * Create or update an `event` object, based on the `eventType`.
	 * @private
	 */
	  var _createEvent = function(event) {
	    var eventType;
	    if (typeof event === "string" && event) {
	      eventType = event;
	      event = {};
	    } else if (typeof event === "object" && event && typeof event.type === "string" && event.type) {
	      eventType = event.type;
	    }
	    if (!eventType) {
	      return;
	    }
	    if (!event.target && /^(copy|aftercopy|_click)$/.test(eventType.toLowerCase())) {
	      event.target = _copyTarget;
	    }
	    _extend(event, {
	      type: eventType.toLowerCase(),
	      target: event.target || _currentElement || null,
	      relatedTarget: event.relatedTarget || null,
	      currentTarget: _flashState && _flashState.bridge || null,
	      timeStamp: event.timeStamp || _now() || null
	    });
	    var msg = _eventMessages[event.type];
	    if (event.type === "error" && event.name && msg) {
	      msg = msg[event.name];
	    }
	    if (msg) {
	      event.message = msg;
	    }
	    if (event.type === "ready") {
	      _extend(event, {
	        target: null,
	        version: _flashState.version
	      });
	    }
	    if (event.type === "error") {
	      if (/^flash-(disabled|outdated|unavailable|deactivated|overdue)$/.test(event.name)) {
	        _extend(event, {
	          target: null,
	          minimumVersion: _minimumFlashVersion
	        });
	      }
	      if (/^flash-(outdated|unavailable|deactivated|overdue)$/.test(event.name)) {
	        _extend(event, {
	          version: _flashState.version
	        });
	      }
	    }
	    if (event.type === "copy") {
	      event.clipboardData = {
	        setData: ZeroClipboard.setData,
	        clearData: ZeroClipboard.clearData
	      };
	    }
	    if (event.type === "aftercopy") {
	      event = _mapClipResultsFromFlash(event, _clipDataFormatMap);
	    }
	    if (event.target && !event.relatedTarget) {
	      event.relatedTarget = _getRelatedTarget(event.target);
	    }
	    event = _addMouseData(event);
	    return event;
	  };
	  /**
	 * Get a relatedTarget from the target's `data-clipboard-target` attribute
	 * @private
	 */
	  var _getRelatedTarget = function(targetEl) {
	    var relatedTargetId = targetEl && targetEl.getAttribute && targetEl.getAttribute("data-clipboard-target");
	    return relatedTargetId ? _document.getElementById(relatedTargetId) : null;
	  };
	  /**
	 * Add element and position data to `MouseEvent` instances
	 * @private
	 */
	  var _addMouseData = function(event) {
	    if (event && /^_(?:click|mouse(?:over|out|down|up|move))$/.test(event.type)) {
	      var srcElement = event.target;
	      var fromElement = event.type === "_mouseover" && event.relatedTarget ? event.relatedTarget : undefined;
	      var toElement = event.type === "_mouseout" && event.relatedTarget ? event.relatedTarget : undefined;
	      var pos = _getDOMObjectPosition(srcElement);
	      var screenLeft = _window.screenLeft || _window.screenX || 0;
	      var screenTop = _window.screenTop || _window.screenY || 0;
	      var scrollLeft = _document.body.scrollLeft + _document.documentElement.scrollLeft;
	      var scrollTop = _document.body.scrollTop + _document.documentElement.scrollTop;
	      var pageX = pos.left + (typeof event._stageX === "number" ? event._stageX : 0);
	      var pageY = pos.top + (typeof event._stageY === "number" ? event._stageY : 0);
	      var clientX = pageX - scrollLeft;
	      var clientY = pageY - scrollTop;
	      var screenX = screenLeft + clientX;
	      var screenY = screenTop + clientY;
	      var moveX = typeof event.movementX === "number" ? event.movementX : 0;
	      var moveY = typeof event.movementY === "number" ? event.movementY : 0;
	      delete event._stageX;
	      delete event._stageY;
	      _extend(event, {
	        srcElement: srcElement,
	        fromElement: fromElement,
	        toElement: toElement,
	        screenX: screenX,
	        screenY: screenY,
	        pageX: pageX,
	        pageY: pageY,
	        clientX: clientX,
	        clientY: clientY,
	        x: clientX,
	        y: clientY,
	        movementX: moveX,
	        movementY: moveY,
	        offsetX: 0,
	        offsetY: 0,
	        layerX: 0,
	        layerY: 0
	      });
	    }
	    return event;
	  };
	  /**
	 * Determine if an event's registered handlers should be execute synchronously or asynchronously.
	 *
	 * @returns {boolean}
	 * @private
	 */
	  var _shouldPerformAsync = function(event) {
	    var eventType = event && typeof event.type === "string" && event.type || "";
	    return !/^(?:(?:before)?copy|destroy)$/.test(eventType);
	  };
	  /**
	 * Control if a callback should be executed asynchronously or not.
	 *
	 * @returns `undefined`
	 * @private
	 */
	  var _dispatchCallback = function(func, context, args, async) {
	    if (async) {
	      _setTimeout(function() {
	        func.apply(context, args);
	      }, 0);
	    } else {
	      func.apply(context, args);
	    }
	  };
	  /**
	 * Handle the actual dispatching of events to client instances.
	 *
	 * @returns `undefined`
	 * @private
	 */
	  var _dispatchCallbacks = function(event) {
	    if (!(typeof event === "object" && event && event.type)) {
	      return;
	    }
	    var async = _shouldPerformAsync(event);
	    var wildcardTypeHandlers = _handlers["*"] || [];
	    var specificTypeHandlers = _handlers[event.type] || [];
	    var handlers = wildcardTypeHandlers.concat(specificTypeHandlers);
	    if (handlers && handlers.length) {
	      var i, len, func, context, eventCopy, originalContext = this;
	      for (i = 0, len = handlers.length; i < len; i++) {
	        func = handlers[i];
	        context = originalContext;
	        if (typeof func === "string" && typeof _window[func] === "function") {
	          func = _window[func];
	        }
	        if (typeof func === "object" && func && typeof func.handleEvent === "function") {
	          context = func;
	          func = func.handleEvent;
	        }
	        if (typeof func === "function") {
	          eventCopy = _extend({}, event);
	          _dispatchCallback(func, context, [ eventCopy ], async);
	        }
	      }
	    }
	    return this;
	  };
	  /**
	 * Preprocess any special behaviors, reactions, or state changes after receiving this event.
	 * Executes only once per event emitted, NOT once per client.
	 * @private
	 */
	  var _preprocessEvent = function(event) {
	    var element = event.target || _currentElement || null;
	    var sourceIsSwf = event._source === "swf";
	    delete event._source;
	    var flashErrorNames = [ "flash-disabled", "flash-outdated", "flash-unavailable", "flash-deactivated", "flash-overdue" ];
	    switch (event.type) {
	     case "error":
	      if (flashErrorNames.indexOf(event.name) !== -1) {
	        _extend(_flashState, {
	          disabled: event.name === "flash-disabled",
	          outdated: event.name === "flash-outdated",
	          unavailable: event.name === "flash-unavailable",
	          deactivated: event.name === "flash-deactivated",
	          overdue: event.name === "flash-overdue",
	          ready: false
	        });
	      }
	      break;

	     case "ready":
	      var wasDeactivated = _flashState.deactivated === true;
	      _extend(_flashState, {
	        disabled: false,
	        outdated: false,
	        unavailable: false,
	        deactivated: false,
	        overdue: wasDeactivated,
	        ready: !wasDeactivated
	      });
	      break;

	     case "beforecopy":
	      _copyTarget = element;
	      break;

	     case "copy":
	      var textContent, htmlContent, targetEl = event.relatedTarget;
	      if (!(_clipData["text/html"] || _clipData["text/plain"]) && targetEl && (htmlContent = targetEl.value || targetEl.outerHTML || targetEl.innerHTML) && (textContent = targetEl.value || targetEl.textContent || targetEl.innerText)) {
	        event.clipboardData.clearData();
	        event.clipboardData.setData("text/plain", textContent);
	        if (htmlContent !== textContent) {
	          event.clipboardData.setData("text/html", htmlContent);
	        }
	      } else if (!_clipData["text/plain"] && event.target && (textContent = event.target.getAttribute("data-clipboard-text"))) {
	        event.clipboardData.clearData();
	        event.clipboardData.setData("text/plain", textContent);
	      }
	      break;

	     case "aftercopy":
	      ZeroClipboard.clearData();
	      if (element && element !== _safeActiveElement() && element.focus) {
	        element.focus();
	      }
	      break;

	     case "_mouseover":
	      ZeroClipboard.focus(element);
	      if (_globalConfig.bubbleEvents === true && sourceIsSwf) {
	        if (element && element !== event.relatedTarget && !_containedBy(event.relatedTarget, element)) {
	          _fireMouseEvent(_extend({}, event, {
	            type: "mouseenter",
	            bubbles: false,
	            cancelable: false
	          }));
	        }
	        _fireMouseEvent(_extend({}, event, {
	          type: "mouseover"
	        }));
	      }
	      break;

	     case "_mouseout":
	      ZeroClipboard.blur();
	      if (_globalConfig.bubbleEvents === true && sourceIsSwf) {
	        if (element && element !== event.relatedTarget && !_containedBy(event.relatedTarget, element)) {
	          _fireMouseEvent(_extend({}, event, {
	            type: "mouseleave",
	            bubbles: false,
	            cancelable: false
	          }));
	        }
	        _fireMouseEvent(_extend({}, event, {
	          type: "mouseout"
	        }));
	      }
	      break;

	     case "_mousedown":
	      _addClass(element, _globalConfig.activeClass);
	      if (_globalConfig.bubbleEvents === true && sourceIsSwf) {
	        _fireMouseEvent(_extend({}, event, {
	          type: event.type.slice(1)
	        }));
	      }
	      break;

	     case "_mouseup":
	      _removeClass(element, _globalConfig.activeClass);
	      if (_globalConfig.bubbleEvents === true && sourceIsSwf) {
	        _fireMouseEvent(_extend({}, event, {
	          type: event.type.slice(1)
	        }));
	      }
	      break;

	     case "_click":
	      _copyTarget = null;
	      if (_globalConfig.bubbleEvents === true && sourceIsSwf) {
	        _fireMouseEvent(_extend({}, event, {
	          type: event.type.slice(1)
	        }));
	      }
	      break;

	     case "_mousemove":
	      if (_globalConfig.bubbleEvents === true && sourceIsSwf) {
	        _fireMouseEvent(_extend({}, event, {
	          type: event.type.slice(1)
	        }));
	      }
	      break;
	    }
	    if (/^_(?:click|mouse(?:over|out|down|up|move))$/.test(event.type)) {
	      return true;
	    }
	  };
	  /**
	 * Dispatch a synthetic MouseEvent.
	 *
	 * @returns `undefined`
	 * @private
	 */
	  var _fireMouseEvent = function(event) {
	    if (!(event && typeof event.type === "string" && event)) {
	      return;
	    }
	    var e, target = event.target || null, doc = target && target.ownerDocument || _document, defaults = {
	      view: doc.defaultView || _window,
	      canBubble: true,
	      cancelable: true,
	      detail: event.type === "click" ? 1 : 0,
	      button: typeof event.which === "number" ? event.which - 1 : typeof event.button === "number" ? event.button : doc.createEvent ? 0 : 1
	    }, args = _extend(defaults, event);
	    if (!target) {
	      return;
	    }
	    if (doc.createEvent && target.dispatchEvent) {
	      args = [ args.type, args.canBubble, args.cancelable, args.view, args.detail, args.screenX, args.screenY, args.clientX, args.clientY, args.ctrlKey, args.altKey, args.shiftKey, args.metaKey, args.button, args.relatedTarget ];
	      e = doc.createEvent("MouseEvents");
	      if (e.initMouseEvent) {
	        e.initMouseEvent.apply(e, args);
	        e._source = "js";
	        target.dispatchEvent(e);
	      }
	    }
	  };
	  /**
	 * Create the HTML bridge element to embed the Flash object into.
	 * @private
	 */
	  var _createHtmlBridge = function() {
	    var container = _document.createElement("div");
	    container.id = _globalConfig.containerId;
	    container.className = _globalConfig.containerClass;
	    container.style.position = "absolute";
	    container.style.left = "0px";
	    container.style.top = "-9999px";
	    container.style.width = "1px";
	    container.style.height = "1px";
	    container.style.zIndex = "" + _getSafeZIndex(_globalConfig.zIndex);
	    return container;
	  };
	  /**
	 * Get the HTML element container that wraps the Flash bridge object/element.
	 * @private
	 */
	  var _getHtmlBridge = function(flashBridge) {
	    var htmlBridge = flashBridge && flashBridge.parentNode;
	    while (htmlBridge && htmlBridge.nodeName === "OBJECT" && htmlBridge.parentNode) {
	      htmlBridge = htmlBridge.parentNode;
	    }
	    return htmlBridge || null;
	  };
	  /**
	 * Create the SWF object.
	 *
	 * @returns The SWF object reference.
	 * @private
	 */
	  var _embedSwf = function() {
	    var len, flashBridge = _flashState.bridge, container = _getHtmlBridge(flashBridge);
	    if (!flashBridge) {
	      var allowScriptAccess = _determineScriptAccess(_window.location.host, _globalConfig);
	      var allowNetworking = allowScriptAccess === "never" ? "none" : "all";
	      var flashvars = _vars(_globalConfig);
	      var swfUrl = _globalConfig.swfPath + _cacheBust(_globalConfig.swfPath, _globalConfig);
	      container = _createHtmlBridge();
	      var divToBeReplaced = _document.createElement("div");
	      container.appendChild(divToBeReplaced);
	      _document.body.appendChild(container);
	      var tmpDiv = _document.createElement("div");
	      var oldIE = _flashState.pluginType === "activex";
	      tmpDiv.innerHTML = '<object id="' + _globalConfig.swfObjectId + '" name="' + _globalConfig.swfObjectId + '" ' + 'width="100%" height="100%" ' + (oldIE ? 'classid="clsid:d27cdb6e-ae6d-11cf-96b8-444553540000"' : 'type="application/x-shockwave-flash" data="' + swfUrl + '"') + ">" + (oldIE ? '<param name="movie" value="' + swfUrl + '"/>' : "") + '<param name="allowScriptAccess" value="' + allowScriptAccess + '"/>' + '<param name="allowNetworking" value="' + allowNetworking + '"/>' + '<param name="menu" value="false"/>' + '<param name="wmode" value="transparent"/>' + '<param name="flashvars" value="' + flashvars + '"/>' + "</object>";
	      flashBridge = tmpDiv.firstChild;
	      tmpDiv = null;
	      _unwrap(flashBridge).ZeroClipboard = ZeroClipboard;
	      container.replaceChild(flashBridge, divToBeReplaced);
	    }
	    if (!flashBridge) {
	      flashBridge = _document[_globalConfig.swfObjectId];
	      if (flashBridge && (len = flashBridge.length)) {
	        flashBridge = flashBridge[len - 1];
	      }
	      if (!flashBridge && container) {
	        flashBridge = container.firstChild;
	      }
	    }
	    _flashState.bridge = flashBridge || null;
	    return flashBridge;
	  };
	  /**
	 * Destroy the SWF object.
	 * @private
	 */
	  var _unembedSwf = function() {
	    var flashBridge = _flashState.bridge;
	    if (flashBridge) {
	      var htmlBridge = _getHtmlBridge(flashBridge);
	      if (htmlBridge) {
	        if (_flashState.pluginType === "activex" && "readyState" in flashBridge) {
	          flashBridge.style.display = "none";
	          (function removeSwfFromIE() {
	            if (flashBridge.readyState === 4) {
	              for (var prop in flashBridge) {
	                if (typeof flashBridge[prop] === "function") {
	                  flashBridge[prop] = null;
	                }
	              }
	              if (flashBridge.parentNode) {
	                flashBridge.parentNode.removeChild(flashBridge);
	              }
	              if (htmlBridge.parentNode) {
	                htmlBridge.parentNode.removeChild(htmlBridge);
	              }
	            } else {
	              _setTimeout(removeSwfFromIE, 10);
	            }
	          })();
	        } else {
	          if (flashBridge.parentNode) {
	            flashBridge.parentNode.removeChild(flashBridge);
	          }
	          if (htmlBridge.parentNode) {
	            htmlBridge.parentNode.removeChild(htmlBridge);
	          }
	        }
	      }
	      _flashState.ready = null;
	      _flashState.bridge = null;
	      _flashState.deactivated = null;
	    }
	  };
	  /**
	 * Map the data format names of the "clipData" to Flash-friendly names.
	 *
	 * @returns A new transformed object.
	 * @private
	 */
	  var _mapClipDataToFlash = function(clipData) {
	    var newClipData = {}, formatMap = {};
	    if (!(typeof clipData === "object" && clipData)) {
	      return;
	    }
	    for (var dataFormat in clipData) {
	      if (dataFormat && _hasOwn.call(clipData, dataFormat) && typeof clipData[dataFormat] === "string" && clipData[dataFormat]) {
	        switch (dataFormat.toLowerCase()) {
	         case "text/plain":
	         case "text":
	         case "air:text":
	         case "flash:text":
	          newClipData.text = clipData[dataFormat];
	          formatMap.text = dataFormat;
	          break;

	         case "text/html":
	         case "html":
	         case "air:html":
	         case "flash:html":
	          newClipData.html = clipData[dataFormat];
	          formatMap.html = dataFormat;
	          break;

	         case "application/rtf":
	         case "text/rtf":
	         case "rtf":
	         case "richtext":
	         case "air:rtf":
	         case "flash:rtf":
	          newClipData.rtf = clipData[dataFormat];
	          formatMap.rtf = dataFormat;
	          break;

	         default:
	          break;
	        }
	      }
	    }
	    return {
	      data: newClipData,
	      formatMap: formatMap
	    };
	  };
	  /**
	 * Map the data format names from Flash-friendly names back to their original "clipData" names (via a format mapping).
	 *
	 * @returns A new transformed object.
	 * @private
	 */
	  var _mapClipResultsFromFlash = function(clipResults, formatMap) {
	    if (!(typeof clipResults === "object" && clipResults && typeof formatMap === "object" && formatMap)) {
	      return clipResults;
	    }
	    var newResults = {};
	    for (var prop in clipResults) {
	      if (_hasOwn.call(clipResults, prop)) {
	        if (prop !== "success" && prop !== "data") {
	          newResults[prop] = clipResults[prop];
	          continue;
	        }
	        newResults[prop] = {};
	        var tmpHash = clipResults[prop];
	        for (var dataFormat in tmpHash) {
	          if (dataFormat && _hasOwn.call(tmpHash, dataFormat) && _hasOwn.call(formatMap, dataFormat)) {
	            newResults[prop][formatMap[dataFormat]] = tmpHash[dataFormat];
	          }
	        }
	      }
	    }
	    return newResults;
	  };
	  /**
	 * Will look at a path, and will create a "?noCache={time}" or "&noCache={time}"
	 * query param string to return. Does NOT append that string to the original path.
	 * This is useful because ExternalInterface often breaks when a Flash SWF is cached.
	 *
	 * @returns The `noCache` query param with necessary "?"/"&" prefix.
	 * @private
	 */
	  var _cacheBust = function(path, options) {
	    var cacheBust = options == null || options && options.cacheBust === true;
	    if (cacheBust) {
	      return (path.indexOf("?") === -1 ? "?" : "&") + "noCache=" + _now();
	    } else {
	      return "";
	    }
	  };
	  /**
	 * Creates a query string for the FlashVars param.
	 * Does NOT include the cache-busting query param.
	 *
	 * @returns FlashVars query string
	 * @private
	 */
	  var _vars = function(options) {
	    var i, len, domain, domains, str = "", trustedOriginsExpanded = [];
	    if (options.trustedDomains) {
	      if (typeof options.trustedDomains === "string") {
	        domains = [ options.trustedDomains ];
	      } else if (typeof options.trustedDomains === "object" && "length" in options.trustedDomains) {
	        domains = options.trustedDomains;
	      }
	    }
	    if (domains && domains.length) {
	      for (i = 0, len = domains.length; i < len; i++) {
	        if (_hasOwn.call(domains, i) && domains[i] && typeof domains[i] === "string") {
	          domain = _extractDomain(domains[i]);
	          if (!domain) {
	            continue;
	          }
	          if (domain === "*") {
	            trustedOriginsExpanded.length = 0;
	            trustedOriginsExpanded.push(domain);
	            break;
	          }
	          trustedOriginsExpanded.push.apply(trustedOriginsExpanded, [ domain, "//" + domain, _window.location.protocol + "//" + domain ]);
	        }
	      }
	    }
	    if (trustedOriginsExpanded.length) {
	      str += "trustedOrigins=" + _encodeURIComponent(trustedOriginsExpanded.join(","));
	    }
	    if (options.forceEnhancedClipboard === true) {
	      str += (str ? "&" : "") + "forceEnhancedClipboard=true";
	    }
	    if (typeof options.swfObjectId === "string" && options.swfObjectId) {
	      str += (str ? "&" : "") + "swfObjectId=" + _encodeURIComponent(options.swfObjectId);
	    }
	    return str;
	  };
	  /**
	 * Extract the domain (e.g. "github.com") from an origin (e.g. "https://github.com") or
	 * URL (e.g. "https://github.com/zeroclipboard/zeroclipboard/").
	 *
	 * @returns the domain
	 * @private
	 */
	  var _extractDomain = function(originOrUrl) {
	    if (originOrUrl == null || originOrUrl === "") {
	      return null;
	    }
	    originOrUrl = originOrUrl.replace(/^\s+|\s+$/g, "");
	    if (originOrUrl === "") {
	      return null;
	    }
	    var protocolIndex = originOrUrl.indexOf("//");
	    originOrUrl = protocolIndex === -1 ? originOrUrl : originOrUrl.slice(protocolIndex + 2);
	    var pathIndex = originOrUrl.indexOf("/");
	    originOrUrl = pathIndex === -1 ? originOrUrl : protocolIndex === -1 || pathIndex === 0 ? null : originOrUrl.slice(0, pathIndex);
	    if (originOrUrl && originOrUrl.slice(-4).toLowerCase() === ".swf") {
	      return null;
	    }
	    return originOrUrl || null;
	  };
	  /**
	 * Set `allowScriptAccess` based on `trustedDomains` and `window.location.host` vs. `swfPath`.
	 *
	 * @returns The appropriate script access level.
	 * @private
	 */
	  var _determineScriptAccess = function() {
	    var _extractAllDomains = function(origins) {
	      var i, len, tmp, resultsArray = [];
	      if (typeof origins === "string") {
	        origins = [ origins ];
	      }
	      if (!(typeof origins === "object" && origins && typeof origins.length === "number")) {
	        return resultsArray;
	      }
	      for (i = 0, len = origins.length; i < len; i++) {
	        if (_hasOwn.call(origins, i) && (tmp = _extractDomain(origins[i]))) {
	          if (tmp === "*") {
	            resultsArray.length = 0;
	            resultsArray.push("*");
	            break;
	          }
	          if (resultsArray.indexOf(tmp) === -1) {
	            resultsArray.push(tmp);
	          }
	        }
	      }
	      return resultsArray;
	    };
	    return function(currentDomain, configOptions) {
	      var swfDomain = _extractDomain(configOptions.swfPath);
	      if (swfDomain === null) {
	        swfDomain = currentDomain;
	      }
	      var trustedDomains = _extractAllDomains(configOptions.trustedDomains);
	      var len = trustedDomains.length;
	      if (len > 0) {
	        if (len === 1 && trustedDomains[0] === "*") {
	          return "always";
	        }
	        if (trustedDomains.indexOf(currentDomain) !== -1) {
	          if (len === 1 && currentDomain === swfDomain) {
	            return "sameDomain";
	          }
	          return "always";
	        }
	      }
	      return "never";
	    };
	  }();
	  /**
	 * Get the currently active/focused DOM element.
	 *
	 * @returns the currently active/focused element, or `null`
	 * @private
	 */
	  var _safeActiveElement = function() {
	    try {
	      return _document.activeElement;
	    } catch (err) {
	      return null;
	    }
	  };
	  /**
	 * Add a class to an element, if it doesn't already have it.
	 *
	 * @returns The element, with its new class added.
	 * @private
	 */
	  var _addClass = function(element, value) {
	    if (!element || element.nodeType !== 1) {
	      return element;
	    }
	    if (element.classList) {
	      if (!element.classList.contains(value)) {
	        element.classList.add(value);
	      }
	      return element;
	    }
	    if (value && typeof value === "string") {
	      var classNames = (value || "").split(/\s+/);
	      if (element.nodeType === 1) {
	        if (!element.className) {
	          element.className = value;
	        } else {
	          var className = " " + element.className + " ", setClass = element.className;
	          for (var c = 0, cl = classNames.length; c < cl; c++) {
	            if (className.indexOf(" " + classNames[c] + " ") < 0) {
	              setClass += " " + classNames[c];
	            }
	          }
	          element.className = setClass.replace(/^\s+|\s+$/g, "");
	        }
	      }
	    }
	    return element;
	  };
	  /**
	 * Remove a class from an element, if it has it.
	 *
	 * @returns The element, with its class removed.
	 * @private
	 */
	  var _removeClass = function(element, value) {
	    if (!element || element.nodeType !== 1) {
	      return element;
	    }
	    if (element.classList) {
	      if (element.classList.contains(value)) {
	        element.classList.remove(value);
	      }
	      return element;
	    }
	    if (typeof value === "string" && value) {
	      var classNames = value.split(/\s+/);
	      if (element.nodeType === 1 && element.className) {
	        var className = (" " + element.className + " ").replace(/[\n\t]/g, " ");
	        for (var c = 0, cl = classNames.length; c < cl; c++) {
	          className = className.replace(" " + classNames[c] + " ", " ");
	        }
	        element.className = className.replace(/^\s+|\s+$/g, "");
	      }
	    }
	    return element;
	  };
	  /**
	 * Attempt to interpret the element's CSS styling. If `prop` is `"cursor"`,
	 * then we assume that it should be a hand ("pointer") cursor if the element
	 * is an anchor element ("a" tag).
	 *
	 * @returns The computed style property.
	 * @private
	 */
	  var _getStyle = function(el, prop) {
	    var value = _window.getComputedStyle(el, null).getPropertyValue(prop);
	    if (prop === "cursor") {
	      if (!value || value === "auto") {
	        if (el.nodeName === "A") {
	          return "pointer";
	        }
	      }
	    }
	    return value;
	  };
	  /**
	 * Get the zoom factor of the browser. Always returns `1.0`, except at
	 * non-default zoom levels in IE<8 and some older versions of WebKit.
	 *
	 * @returns Floating unit percentage of the zoom factor (e.g. 150% = `1.5`).
	 * @private
	 */
	  var _getZoomFactor = function() {
	    var rect, physicalWidth, logicalWidth, zoomFactor = 1;
	    if (typeof _document.body.getBoundingClientRect === "function") {
	      rect = _document.body.getBoundingClientRect();
	      physicalWidth = rect.right - rect.left;
	      logicalWidth = _document.body.offsetWidth;
	      zoomFactor = _round(physicalWidth / logicalWidth * 100) / 100;
	    }
	    return zoomFactor;
	  };
	  /**
	 * Get the DOM positioning info of an element.
	 *
	 * @returns Object containing the element's position, width, and height.
	 * @private
	 */
	  var _getDOMObjectPosition = function(obj) {
	    var info = {
	      left: 0,
	      top: 0,
	      width: 0,
	      height: 0
	    };
	    if (obj.getBoundingClientRect) {
	      var rect = obj.getBoundingClientRect();
	      var pageXOffset, pageYOffset, zoomFactor;
	      if ("pageXOffset" in _window && "pageYOffset" in _window) {
	        pageXOffset = _window.pageXOffset;
	        pageYOffset = _window.pageYOffset;
	      } else {
	        zoomFactor = _getZoomFactor();
	        pageXOffset = _round(_document.documentElement.scrollLeft / zoomFactor);
	        pageYOffset = _round(_document.documentElement.scrollTop / zoomFactor);
	      }
	      var leftBorderWidth = _document.documentElement.clientLeft || 0;
	      var topBorderWidth = _document.documentElement.clientTop || 0;
	      info.left = rect.left + pageXOffset - leftBorderWidth;
	      info.top = rect.top + pageYOffset - topBorderWidth;
	      info.width = "width" in rect ? rect.width : rect.right - rect.left;
	      info.height = "height" in rect ? rect.height : rect.bottom - rect.top;
	    }
	    return info;
	  };
	  /**
	 * Reposition the Flash object to cover the currently activated element.
	 *
	 * @returns `undefined`
	 * @private
	 */
	  var _reposition = function() {
	    var htmlBridge;
	    if (_currentElement && (htmlBridge = _getHtmlBridge(_flashState.bridge))) {
	      var pos = _getDOMObjectPosition(_currentElement);
	      _extend(htmlBridge.style, {
	        width: pos.width + "px",
	        height: pos.height + "px",
	        top: pos.top + "px",
	        left: pos.left + "px",
	        zIndex: "" + _getSafeZIndex(_globalConfig.zIndex)
	      });
	    }
	  };
	  /**
	 * Sends a signal to the Flash object to display the hand cursor if `true`.
	 *
	 * @returns `undefined`
	 * @private
	 */
	  var _setHandCursor = function(enabled) {
	    if (_flashState.ready === true) {
	      if (_flashState.bridge && typeof _flashState.bridge.setHandCursor === "function") {
	        _flashState.bridge.setHandCursor(enabled);
	      } else {
	        _flashState.ready = false;
	      }
	    }
	  };
	  /**
	 * Get a safe value for `zIndex`
	 *
	 * @returns an integer, or "auto"
	 * @private
	 */
	  var _getSafeZIndex = function(val) {
	    if (/^(?:auto|inherit)$/.test(val)) {
	      return val;
	    }
	    var zIndex;
	    if (typeof val === "number" && !_isNaN(val)) {
	      zIndex = val;
	    } else if (typeof val === "string") {
	      zIndex = _getSafeZIndex(_parseInt(val, 10));
	    }
	    return typeof zIndex === "number" ? zIndex : "auto";
	  };
	  /**
	 * Detect the Flash Player status, version, and plugin type.
	 *
	 * @see {@link https://code.google.com/p/doctype-mirror/wiki/ArticleDetectFlash#The_code}
	 * @see {@link http://stackoverflow.com/questions/12866060/detecting-pepper-ppapi-flash-with-javascript}
	 *
	 * @returns `undefined`
	 * @private
	 */
	  var _detectFlashSupport = function(ActiveXObject) {
	    var plugin, ax, mimeType, hasFlash = false, isActiveX = false, isPPAPI = false, flashVersion = "";
	    /**
	   * Derived from Apple's suggested sniffer.
	   * @param {String} desc e.g. "Shockwave Flash 7.0 r61"
	   * @returns {String} "7.0.61"
	   * @private
	   */
	    function parseFlashVersion(desc) {
	      var matches = desc.match(/[\d]+/g);
	      matches.length = 3;
	      return matches.join(".");
	    }
	    function isPepperFlash(flashPlayerFileName) {
	      return !!flashPlayerFileName && (flashPlayerFileName = flashPlayerFileName.toLowerCase()) && (/^(pepflashplayer\.dll|libpepflashplayer\.so|pepperflashplayer\.plugin)$/.test(flashPlayerFileName) || flashPlayerFileName.slice(-13) === "chrome.plugin");
	    }
	    function inspectPlugin(plugin) {
	      if (plugin) {
	        hasFlash = true;
	        if (plugin.version) {
	          flashVersion = parseFlashVersion(plugin.version);
	        }
	        if (!flashVersion && plugin.description) {
	          flashVersion = parseFlashVersion(plugin.description);
	        }
	        if (plugin.filename) {
	          isPPAPI = isPepperFlash(plugin.filename);
	        }
	      }
	    }
	    if (_navigator.plugins && _navigator.plugins.length) {
	      plugin = _navigator.plugins["Shockwave Flash"];
	      inspectPlugin(plugin);
	      if (_navigator.plugins["Shockwave Flash 2.0"]) {
	        hasFlash = true;
	        flashVersion = "2.0.0.11";
	      }
	    } else if (_navigator.mimeTypes && _navigator.mimeTypes.length) {
	      mimeType = _navigator.mimeTypes["application/x-shockwave-flash"];
	      plugin = mimeType && mimeType.enabledPlugin;
	      inspectPlugin(plugin);
	    } else if (typeof ActiveXObject !== "undefined") {
	      isActiveX = true;
	      try {
	        ax = new ActiveXObject("ShockwaveFlash.ShockwaveFlash.7");
	        hasFlash = true;
	        flashVersion = parseFlashVersion(ax.GetVariable("$version"));
	      } catch (e1) {
	        try {
	          ax = new ActiveXObject("ShockwaveFlash.ShockwaveFlash.6");
	          hasFlash = true;
	          flashVersion = "6.0.21";
	        } catch (e2) {
	          try {
	            ax = new ActiveXObject("ShockwaveFlash.ShockwaveFlash");
	            hasFlash = true;
	            flashVersion = parseFlashVersion(ax.GetVariable("$version"));
	          } catch (e3) {
	            isActiveX = false;
	          }
	        }
	      }
	    }
	    _flashState.disabled = hasFlash !== true;
	    _flashState.outdated = flashVersion && _parseFloat(flashVersion) < _parseFloat(_minimumFlashVersion);
	    _flashState.version = flashVersion || "0.0.0";
	    _flashState.pluginType = isPPAPI ? "pepper" : isActiveX ? "activex" : hasFlash ? "netscape" : "unknown";
	  };
	  /**
	 * Invoke the Flash detection algorithms immediately upon inclusion so we're not waiting later.
	 */
	  _detectFlashSupport(_ActiveXObject);
	  /**
	 * A shell constructor for `ZeroClipboard` client instances.
	 *
	 * @constructor
	 */
	  var ZeroClipboard = function() {
	    if (!(this instanceof ZeroClipboard)) {
	      return new ZeroClipboard();
	    }
	    if (typeof ZeroClipboard._createClient === "function") {
	      ZeroClipboard._createClient.apply(this, _args(arguments));
	    }
	  };
	  /**
	 * The ZeroClipboard library's version number.
	 *
	 * @static
	 * @readonly
	 * @property {string}
	 */
	  _defineProperty(ZeroClipboard, "version", {
	    value: "2.1.6",
	    writable: false,
	    configurable: true,
	    enumerable: true
	  });
	  /**
	 * Update or get a copy of the ZeroClipboard global configuration.
	 * Returns a copy of the current/updated configuration.
	 *
	 * @returns Object
	 * @static
	 */
	  ZeroClipboard.config = function() {
	    return _config.apply(this, _args(arguments));
	  };
	  /**
	 * Diagnostic method that describes the state of the browser, Flash Player, and ZeroClipboard.
	 *
	 * @returns Object
	 * @static
	 */
	  ZeroClipboard.state = function() {
	    return _state.apply(this, _args(arguments));
	  };
	  /**
	 * Check if Flash is unusable for any reason: disabled, outdated, deactivated, etc.
	 *
	 * @returns Boolean
	 * @static
	 */
	  ZeroClipboard.isFlashUnusable = function() {
	    return _isFlashUnusable.apply(this, _args(arguments));
	  };
	  /**
	 * Register an event listener.
	 *
	 * @returns `ZeroClipboard`
	 * @static
	 */
	  ZeroClipboard.on = function() {
	    return _on.apply(this, _args(arguments));
	  };
	  /**
	 * Unregister an event listener.
	 * If no `listener` function/object is provided, it will unregister all listeners for the provided `eventType`.
	 * If no `eventType` is provided, it will unregister all listeners for every event type.
	 *
	 * @returns `ZeroClipboard`
	 * @static
	 */
	  ZeroClipboard.off = function() {
	    return _off.apply(this, _args(arguments));
	  };
	  /**
	 * Retrieve event listeners for an `eventType`.
	 * If no `eventType` is provided, it will retrieve all listeners for every event type.
	 *
	 * @returns array of listeners for the `eventType`; if no `eventType`, then a map/hash object of listeners for all event types; or `null`
	 */
	  ZeroClipboard.handlers = function() {
	    return _listeners.apply(this, _args(arguments));
	  };
	  /**
	 * Event emission receiver from the Flash object, forwarding to any registered JavaScript event listeners.
	 *
	 * @returns For the "copy" event, returns the Flash-friendly "clipData" object; otherwise `undefined`.
	 * @static
	 */
	  ZeroClipboard.emit = function() {
	    return _emit.apply(this, _args(arguments));
	  };
	  /**
	 * Create and embed the Flash object.
	 *
	 * @returns The Flash object
	 * @static
	 */
	  ZeroClipboard.create = function() {
	    return _create.apply(this, _args(arguments));
	  };
	  /**
	 * Self-destruct and clean up everything, including the embedded Flash object.
	 *
	 * @returns `undefined`
	 * @static
	 */
	  ZeroClipboard.destroy = function() {
	    return _destroy.apply(this, _args(arguments));
	  };
	  /**
	 * Set the pending data for clipboard injection.
	 *
	 * @returns `undefined`
	 * @static
	 */
	  ZeroClipboard.setData = function() {
	    return _setData.apply(this, _args(arguments));
	  };
	  /**
	 * Clear the pending data for clipboard injection.
	 * If no `format` is provided, all pending data formats will be cleared.
	 *
	 * @returns `undefined`
	 * @static
	 */
	  ZeroClipboard.clearData = function() {
	    return _clearData.apply(this, _args(arguments));
	  };
	  /**
	 * Get a copy of the pending data for clipboard injection.
	 * If no `format` is provided, a copy of ALL pending data formats will be returned.
	 *
	 * @returns `String` or `Object`
	 * @static
	 */
	  ZeroClipboard.getData = function() {
	    return _getData.apply(this, _args(arguments));
	  };
	  /**
	 * Sets the current HTML object that the Flash object should overlay. This will put the global
	 * Flash object on top of the current element; depending on the setup, this may also set the
	 * pending clipboard text data as well as the Flash object's wrapping element's title attribute
	 * based on the underlying HTML element and ZeroClipboard configuration.
	 *
	 * @returns `undefined`
	 * @static
	 */
	  ZeroClipboard.focus = ZeroClipboard.activate = function() {
	    return _focus.apply(this, _args(arguments));
	  };
	  /**
	 * Un-overlays the Flash object. This will put the global Flash object off-screen; depending on
	 * the setup, this may also unset the Flash object's wrapping element's title attribute based on
	 * the underlying HTML element and ZeroClipboard configuration.
	 *
	 * @returns `undefined`
	 * @static
	 */
	  ZeroClipboard.blur = ZeroClipboard.deactivate = function() {
	    return _blur.apply(this, _args(arguments));
	  };
	  /**
	 * Returns the currently focused/"activated" HTML element that the Flash object is wrapping.
	 *
	 * @returns `HTMLElement` or `null`
	 * @static
	 */
	  ZeroClipboard.activeElement = function() {
	    return _activeElement.apply(this, _args(arguments));
	  };
	  /**
	 * Keep track of the ZeroClipboard client instance counter.
	 */
	  var _clientIdCounter = 0;
	  /**
	 * Keep track of the state of the client instances.
	 *
	 * Entry structure:
	 *   _clientMeta[client.id] = {
	 *     instance: client,
	 *     elements: [],
	 *     handlers: {}
	 *   };
	 */
	  var _clientMeta = {};
	  /**
	 * Keep track of the ZeroClipboard clipped elements counter.
	 */
	  var _elementIdCounter = 0;
	  /**
	 * Keep track of the state of the clipped element relationships to clients.
	 *
	 * Entry structure:
	 *   _elementMeta[element.zcClippingId] = [client1.id, client2.id];
	 */
	  var _elementMeta = {};
	  /**
	 * Keep track of the state of the mouse event handlers for clipped elements.
	 *
	 * Entry structure:
	 *   _mouseHandlers[element.zcClippingId] = {
	 *     mouseover:  function(event) {},
	 *     mouseout:   function(event) {},
	 *     mouseenter: function(event) {},
	 *     mouseleave: function(event) {},
	 *     mousemove:  function(event) {}
	 *   };
	 */
	  var _mouseHandlers = {};
	  /**
	 * Extending the ZeroClipboard configuration defaults for the Client module.
	 */
	  _extend(_globalConfig, {
	    autoActivate: true
	  });
	  /**
	 * The real constructor for `ZeroClipboard` client instances.
	 * @private
	 */
	  var _clientConstructor = function(elements) {
	    var client = this;
	    client.id = "" + _clientIdCounter++;
	    _clientMeta[client.id] = {
	      instance: client,
	      elements: [],
	      handlers: {}
	    };
	    if (elements) {
	      client.clip(elements);
	    }
	    ZeroClipboard.on("*", function(event) {
	      return client.emit(event);
	    });
	    ZeroClipboard.on("destroy", function() {
	      client.destroy();
	    });
	    ZeroClipboard.create();
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.Client.prototype.on`.
	 * @private
	 */
	  var _clientOn = function(eventType, listener) {
	    var i, len, events, added = {}, handlers = _clientMeta[this.id] && _clientMeta[this.id].handlers;
	    if (typeof eventType === "string" && eventType) {
	      events = eventType.toLowerCase().split(/\s+/);
	    } else if (typeof eventType === "object" && eventType && typeof listener === "undefined") {
	      for (i in eventType) {
	        if (_hasOwn.call(eventType, i) && typeof i === "string" && i && typeof eventType[i] === "function") {
	          this.on(i, eventType[i]);
	        }
	      }
	    }
	    if (events && events.length) {
	      for (i = 0, len = events.length; i < len; i++) {
	        eventType = events[i].replace(/^on/, "");
	        added[eventType] = true;
	        if (!handlers[eventType]) {
	          handlers[eventType] = [];
	        }
	        handlers[eventType].push(listener);
	      }
	      if (added.ready && _flashState.ready) {
	        this.emit({
	          type: "ready",
	          client: this
	        });
	      }
	      if (added.error) {
	        var errorTypes = [ "disabled", "outdated", "unavailable", "deactivated", "overdue" ];
	        for (i = 0, len = errorTypes.length; i < len; i++) {
	          if (_flashState[errorTypes[i]]) {
	            this.emit({
	              type: "error",
	              name: "flash-" + errorTypes[i],
	              client: this
	            });
	            break;
	          }
	        }
	      }
	    }
	    return this;
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.Client.prototype.off`.
	 * @private
	 */
	  var _clientOff = function(eventType, listener) {
	    var i, len, foundIndex, events, perEventHandlers, handlers = _clientMeta[this.id] && _clientMeta[this.id].handlers;
	    if (arguments.length === 0) {
	      events = _keys(handlers);
	    } else if (typeof eventType === "string" && eventType) {
	      events = eventType.split(/\s+/);
	    } else if (typeof eventType === "object" && eventType && typeof listener === "undefined") {
	      for (i in eventType) {
	        if (_hasOwn.call(eventType, i) && typeof i === "string" && i && typeof eventType[i] === "function") {
	          this.off(i, eventType[i]);
	        }
	      }
	    }
	    if (events && events.length) {
	      for (i = 0, len = events.length; i < len; i++) {
	        eventType = events[i].toLowerCase().replace(/^on/, "");
	        perEventHandlers = handlers[eventType];
	        if (perEventHandlers && perEventHandlers.length) {
	          if (listener) {
	            foundIndex = perEventHandlers.indexOf(listener);
	            while (foundIndex !== -1) {
	              perEventHandlers.splice(foundIndex, 1);
	              foundIndex = perEventHandlers.indexOf(listener, foundIndex);
	            }
	          } else {
	            perEventHandlers.length = 0;
	          }
	        }
	      }
	    }
	    return this;
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.Client.prototype.handlers`.
	 * @private
	 */
	  var _clientListeners = function(eventType) {
	    var copy = null, handlers = _clientMeta[this.id] && _clientMeta[this.id].handlers;
	    if (handlers) {
	      if (typeof eventType === "string" && eventType) {
	        copy = handlers[eventType] ? handlers[eventType].slice(0) : [];
	      } else {
	        copy = _deepCopy(handlers);
	      }
	    }
	    return copy;
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.Client.prototype.emit`.
	 * @private
	 */
	  var _clientEmit = function(event) {
	    if (_clientShouldEmit.call(this, event)) {
	      if (typeof event === "object" && event && typeof event.type === "string" && event.type) {
	        event = _extend({}, event);
	      }
	      var eventCopy = _extend({}, _createEvent(event), {
	        client: this
	      });
	      _clientDispatchCallbacks.call(this, eventCopy);
	    }
	    return this;
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.Client.prototype.clip`.
	 * @private
	 */
	  var _clientClip = function(elements) {
	    elements = _prepClip(elements);
	    for (var i = 0; i < elements.length; i++) {
	      if (_hasOwn.call(elements, i) && elements[i] && elements[i].nodeType === 1) {
	        if (!elements[i].zcClippingId) {
	          elements[i].zcClippingId = "zcClippingId_" + _elementIdCounter++;
	          _elementMeta[elements[i].zcClippingId] = [ this.id ];
	          if (_globalConfig.autoActivate === true) {
	            _addMouseHandlers(elements[i]);
	          }
	        } else if (_elementMeta[elements[i].zcClippingId].indexOf(this.id) === -1) {
	          _elementMeta[elements[i].zcClippingId].push(this.id);
	        }
	        var clippedElements = _clientMeta[this.id] && _clientMeta[this.id].elements;
	        if (clippedElements.indexOf(elements[i]) === -1) {
	          clippedElements.push(elements[i]);
	        }
	      }
	    }
	    return this;
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.Client.prototype.unclip`.
	 * @private
	 */
	  var _clientUnclip = function(elements) {
	    var meta = _clientMeta[this.id];
	    if (!meta) {
	      return this;
	    }
	    var clippedElements = meta.elements;
	    var arrayIndex;
	    if (typeof elements === "undefined") {
	      elements = clippedElements.slice(0);
	    } else {
	      elements = _prepClip(elements);
	    }
	    for (var i = elements.length; i--; ) {
	      if (_hasOwn.call(elements, i) && elements[i] && elements[i].nodeType === 1) {
	        arrayIndex = 0;
	        while ((arrayIndex = clippedElements.indexOf(elements[i], arrayIndex)) !== -1) {
	          clippedElements.splice(arrayIndex, 1);
	        }
	        var clientIds = _elementMeta[elements[i].zcClippingId];
	        if (clientIds) {
	          arrayIndex = 0;
	          while ((arrayIndex = clientIds.indexOf(this.id, arrayIndex)) !== -1) {
	            clientIds.splice(arrayIndex, 1);
	          }
	          if (clientIds.length === 0) {
	            if (_globalConfig.autoActivate === true) {
	              _removeMouseHandlers(elements[i]);
	            }
	            delete elements[i].zcClippingId;
	          }
	        }
	      }
	    }
	    return this;
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.Client.prototype.elements`.
	 * @private
	 */
	  var _clientElements = function() {
	    var meta = _clientMeta[this.id];
	    return meta && meta.elements ? meta.elements.slice(0) : [];
	  };
	  /**
	 * The underlying implementation of `ZeroClipboard.Client.prototype.destroy`.
	 * @private
	 */
	  var _clientDestroy = function() {
	    this.unclip();
	    this.off();
	    delete _clientMeta[this.id];
	  };
	  /**
	 * Inspect an Event to see if the Client (`this`) should honor it for emission.
	 * @private
	 */
	  var _clientShouldEmit = function(event) {
	    if (!(event && event.type)) {
	      return false;
	    }
	    if (event.client && event.client !== this) {
	      return false;
	    }
	    var clippedEls = _clientMeta[this.id] && _clientMeta[this.id].elements;
	    var hasClippedEls = !!clippedEls && clippedEls.length > 0;
	    var goodTarget = !event.target || hasClippedEls && clippedEls.indexOf(event.target) !== -1;
	    var goodRelTarget = event.relatedTarget && hasClippedEls && clippedEls.indexOf(event.relatedTarget) !== -1;
	    var goodClient = event.client && event.client === this;
	    if (!(goodTarget || goodRelTarget || goodClient)) {
	      return false;
	    }
	    return true;
	  };
	  /**
	 * Handle the actual dispatching of events to a client instance.
	 *
	 * @returns `this`
	 * @private
	 */
	  var _clientDispatchCallbacks = function(event) {
	    if (!(typeof event === "object" && event && event.type)) {
	      return;
	    }
	    var async = _shouldPerformAsync(event);
	    var wildcardTypeHandlers = _clientMeta[this.id] && _clientMeta[this.id].handlers["*"] || [];
	    var specificTypeHandlers = _clientMeta[this.id] && _clientMeta[this.id].handlers[event.type] || [];
	    var handlers = wildcardTypeHandlers.concat(specificTypeHandlers);
	    if (handlers && handlers.length) {
	      var i, len, func, context, eventCopy, originalContext = this;
	      for (i = 0, len = handlers.length; i < len; i++) {
	        func = handlers[i];
	        context = originalContext;
	        if (typeof func === "string" && typeof _window[func] === "function") {
	          func = _window[func];
	        }
	        if (typeof func === "object" && func && typeof func.handleEvent === "function") {
	          context = func;
	          func = func.handleEvent;
	        }
	        if (typeof func === "function") {
	          eventCopy = _extend({}, event);
	          _dispatchCallback(func, context, [ eventCopy ], async);
	        }
	      }
	    }
	    return this;
	  };
	  /**
	 * Prepares the elements for clipping/unclipping.
	 *
	 * @returns An Array of elements.
	 * @private
	 */
	  var _prepClip = function(elements) {
	    if (typeof elements === "string") {
	      elements = [];
	    }
	    return typeof elements.length !== "number" ? [ elements ] : elements;
	  };
	  /**
	 * Add a `mouseover` handler function for a clipped element.
	 *
	 * @returns `undefined`
	 * @private
	 */
	  var _addMouseHandlers = function(element) {
	    if (!(element && element.nodeType === 1)) {
	      return;
	    }
	    var _suppressMouseEvents = function(event) {
	      if (!(event || (event = _window.event))) {
	        return;
	      }
	      if (event._source !== "js") {
	        event.stopImmediatePropagation();
	        event.preventDefault();
	      }
	      delete event._source;
	    };
	    var _elementMouseOver = function(event) {
	      if (!(event || (event = _window.event))) {
	        return;
	      }
	      _suppressMouseEvents(event);
	      ZeroClipboard.focus(element);
	    };
	    element.addEventListener("mouseover", _elementMouseOver, false);
	    element.addEventListener("mouseout", _suppressMouseEvents, false);
	    element.addEventListener("mouseenter", _suppressMouseEvents, false);
	    element.addEventListener("mouseleave", _suppressMouseEvents, false);
	    element.addEventListener("mousemove", _suppressMouseEvents, false);
	    _mouseHandlers[element.zcClippingId] = {
	      mouseover: _elementMouseOver,
	      mouseout: _suppressMouseEvents,
	      mouseenter: _suppressMouseEvents,
	      mouseleave: _suppressMouseEvents,
	      mousemove: _suppressMouseEvents
	    };
	  };
	  /**
	 * Remove a `mouseover` handler function for a clipped element.
	 *
	 * @returns `undefined`
	 * @private
	 */
	  var _removeMouseHandlers = function(element) {
	    if (!(element && element.nodeType === 1)) {
	      return;
	    }
	    var mouseHandlers = _mouseHandlers[element.zcClippingId];
	    if (!(typeof mouseHandlers === "object" && mouseHandlers)) {
	      return;
	    }
	    var key, val, mouseEvents = [ "move", "leave", "enter", "out", "over" ];
	    for (var i = 0, len = mouseEvents.length; i < len; i++) {
	      key = "mouse" + mouseEvents[i];
	      val = mouseHandlers[key];
	      if (typeof val === "function") {
	        element.removeEventListener(key, val, false);
	      }
	    }
	    delete _mouseHandlers[element.zcClippingId];
	  };
	  /**
	 * Creates a new ZeroClipboard client instance.
	 * Optionally, auto-`clip` an element or collection of elements.
	 *
	 * @constructor
	 */
	  ZeroClipboard._createClient = function() {
	    _clientConstructor.apply(this, _args(arguments));
	  };
	  /**
	 * Register an event listener to the client.
	 *
	 * @returns `this`
	 */
	  ZeroClipboard.prototype.on = function() {
	    return _clientOn.apply(this, _args(arguments));
	  };
	  /**
	 * Unregister an event handler from the client.
	 * If no `listener` function/object is provided, it will unregister all handlers for the provided `eventType`.
	 * If no `eventType` is provided, it will unregister all handlers for every event type.
	 *
	 * @returns `this`
	 */
	  ZeroClipboard.prototype.off = function() {
	    return _clientOff.apply(this, _args(arguments));
	  };
	  /**
	 * Retrieve event listeners for an `eventType` from the client.
	 * If no `eventType` is provided, it will retrieve all listeners for every event type.
	 *
	 * @returns array of listeners for the `eventType`; if no `eventType`, then a map/hash object of listeners for all event types; or `null`
	 */
	  ZeroClipboard.prototype.handlers = function() {
	    return _clientListeners.apply(this, _args(arguments));
	  };
	  /**
	 * Event emission receiver from the Flash object for this client's registered JavaScript event listeners.
	 *
	 * @returns For the "copy" event, returns the Flash-friendly "clipData" object; otherwise `undefined`.
	 */
	  ZeroClipboard.prototype.emit = function() {
	    return _clientEmit.apply(this, _args(arguments));
	  };
	  /**
	 * Register clipboard actions for new element(s) to the client.
	 *
	 * @returns `this`
	 */
	  ZeroClipboard.prototype.clip = function() {
	    return _clientClip.apply(this, _args(arguments));
	  };
	  /**
	 * Unregister the clipboard actions of previously registered element(s) on the page.
	 * If no elements are provided, ALL registered elements will be unregistered.
	 *
	 * @returns `this`
	 */
	  ZeroClipboard.prototype.unclip = function() {
	    return _clientUnclip.apply(this, _args(arguments));
	  };
	  /**
	 * Get all of the elements to which this client is clipped.
	 *
	 * @returns array of clipped elements
	 */
	  ZeroClipboard.prototype.elements = function() {
	    return _clientElements.apply(this, _args(arguments));
	  };
	  /**
	 * Self-destruct and clean up everything for a single client.
	 * This will NOT destroy the embedded Flash object.
	 *
	 * @returns `undefined`
	 */
	  ZeroClipboard.prototype.destroy = function() {
	    return _clientDestroy.apply(this, _args(arguments));
	  };
	  /**
	 * Stores the pending plain text to inject into the clipboard.
	 *
	 * @returns `this`
	 */
	  ZeroClipboard.prototype.setText = function(text) {
	    ZeroClipboard.setData("text/plain", text);
	    return this;
	  };
	  /**
	 * Stores the pending HTML text to inject into the clipboard.
	 *
	 * @returns `this`
	 */
	  ZeroClipboard.prototype.setHtml = function(html) {
	    ZeroClipboard.setData("text/html", html);
	    return this;
	  };
	  /**
	 * Stores the pending rich text (RTF) to inject into the clipboard.
	 *
	 * @returns `this`
	 */
	  ZeroClipboard.prototype.setRichText = function(richText) {
	    ZeroClipboard.setData("application/rtf", richText);
	    return this;
	  };
	  /**
	 * Stores the pending data to inject into the clipboard.
	 *
	 * @returns `this`
	 */
	  ZeroClipboard.prototype.setData = function() {
	    ZeroClipboard.setData.apply(this, _args(arguments));
	    return this;
	  };
	  /**
	 * Clears the pending data to inject into the clipboard.
	 * If no `format` is provided, all pending data formats will be cleared.
	 *
	 * @returns `this`
	 */
	  ZeroClipboard.prototype.clearData = function() {
	    ZeroClipboard.clearData.apply(this, _args(arguments));
	    return this;
	  };
	  /**
	 * Gets a copy of the pending data to inject into the clipboard.
	 * If no `format` is provided, a copy of ALL pending data formats will be returned.
	 *
	 * @returns `String` or `Object`
	 */
	  ZeroClipboard.prototype.getData = function() {
	    return ZeroClipboard.getData.apply(this, _args(arguments));
	  };
	  if (false) {
	    define(function() {
	      return ZeroClipboard;
	    });
	  } else if (typeof module === "object" && module && typeof module.exports === "object" && module.exports) {
	    module.exports = ZeroClipboard;
	  } else {
	    window.ZeroClipboard = ZeroClipboard;
	  }
	})(function() {
	  return this || window;
	}());
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(81)(module)))

/***/ }

});
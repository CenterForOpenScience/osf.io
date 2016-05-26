/**
* A simple folder picker plugin built on HGrid.
* Takes the same options as HGrid and additionally requires an
* `onPickFolder` option (the callback executed when a folder is selected).
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
var $ = require('jquery');
var m = require('mithril');
var Treebeard = require('treebeard');


function treebeardToggleCheck(item) {
    return ((typeof item.data.hasChildren === 'undefined') || item.data.hasChildren);
}

function treebeardResolveToggle(item) {
    if ((typeof item.data.hasChildren !== 'undefined') && item.data.hasChildren === false) {
        return '';
    }

    return item.open ?
        m('i.fa.fa-minus', ' '):
        m('i.fa.fa-plus', ' ');
}

// Returns custom icons for OSF
function treebeardResolveIcon(item) {
    return item.open ?
        m('i.fa.fa-folder-open-o', ' '):
        m('i.fa.fa-folder-o', ' ');
}

var INPUT_NAME = '-folder-select';

function treebeardTitleColumn(item, col) {
    var tb = this; // jshint ignore: line

    var cls = '';
    var onclick = function() {};
    if (typeof item.data.hasChildren === 'undefined' || item.data.hasChildren) {
        cls = 'hasChildren';
        onclick = function() {
            tb.updateFolder(null, item);
        };
    }

    return m('span', {
        className: cls,
        onclick: onclick
    }, tb.options.decodeFolder(item.data.name));
}

/**
 * Returns the folder select button for a single row.
 */
function treebeardSelectView(item) {
    var tb = this; // jshint ignore: line
    var setTempPicked = function() {
        this._tempPicked = item.id;
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
        onmousedown: function(evt) {
            tb.options.onPickFolder(evt, item);
        },
        name: '#' + tb.options.divID + INPUT_NAME
    }, ' ');

    if (tb._tempPicked) {
        if (tb._tempPicked === item.id) {
            return templateChecked;
        }
        return templateUnchecked;
    }

    if (item.data.path === tb.options.folderPath || (tb.options.folderArray && tb.options.folderArray[tb.options.folderArray.length - 1] === item.data.name)) {
        return templateChecked;
    }

    return templateUnchecked;
}

function treebeardColumnTitle() {
    return [{
        title: 'Folders',
        width: '75%',
        sort: false
    }, {
        title: 'Select',
        width: '25%',
        sort: false
    }];
}

function treebeardResolveRows(item) {
    // this = treebeard;
    item.css = '';
    return [{
        data: 'name', // Data field name
        folderIcons: true,
        filter: false,
        custom: treebeardTitleColumn
    }, {
        sortInclude: false,
        css: 'p-l-xs',
        custom: treebeardSelectView
    }];
}

function treebeardOnload() {
    var tb = this; // jshint ignore: line

    tb.options.folderIndex = 0;
    if (tb.options.folderPath) {
        tb.options.folderArray = tb.options.folderPath.split('/');
        if (tb.options.folderArray.length > 1) {
            tb.options.folderArray.splice(0, 1);
        }
    } else {
        tb.options.folderArray = [''];
    }

    var node = tb.treeData.children[0];
    if ((typeof node.data.hasChildren === 'undefined') || node.data.hasChildren) {
        tb.updateFolder(null, tb.treeData.children[0]);
    }
    tb.options.folderPickerOnload();
}

function treebeardLazyLoadOnLoad(item) {
    var tb = this; // jshint ignore: line

    for (var i = 0; i < item.children.length; i++) {
        if ((typeof item.data.hasChildren !== 'undefined') && item.data.hasChildren === false) {
            return;
        }
        if (item.children[i].data.name === tb.options.folderArray[tb.options.folderIndex]) {
            tb.updateFolder(null, item.children[i]);
            tb.options.folderIndex++;
            return;
        }
    }
}

function treebeardDecodeFolder(item) {
    return item;
}

// Default Treebeard options
var defaults = {
    columnTitles: treebeardColumnTitle,
    resolveRows: treebeardResolveRows,
    resolveIcon: treebeardResolveIcon,
    togglecheck: treebeardToggleCheck,
    resolveToggle: treebeardResolveToggle,
    ondataload: treebeardOnload,
    lazyLoadOnLoad: treebeardLazyLoadOnLoad,
    decodeFolder: treebeardDecodeFolder,
    // Disable uploads
    uploads: false,
    showFilter : false,
    resizeColumns : false,
    rowHeight : 35,
    resolveRefreshIcon : function() {
        return m('i.fa.fa-refresh.fa-spin');
    }
};

function FolderPicker(selector, opts) {
    var self = this;
    self.selector = selector;
    self.checkedRowId = null;
    // Custom Treebeard action to select a folder that uses the passed in
    // "onChooseFolder" callback
    if (!opts.onPickFolder) {
        throw new Error('FolderPicker must have the "onPickFolder" option defined');
    }
    self.options = $.extend({}, defaults, opts);
    self.options.divID = selector.substring(1);
    self.options.initialFolderName = opts.initialFolderName;
    self.options.folderPath = opts.initialFolderPath;
    self.options.rootName = opts.rootName;

    // Start up the grid
    self.grid = new Treebeard(self.options);
}

FolderPicker.prototype.destroy = function() {
    this.grid.destroy();
};

// Augment jQuery
$.fn.folderpicker = function(options) {
    var $el = $(this);
    this.each(function() {
        // Treebeard must take an ID as a selector if using as a jQuery plugin
        if (!this.id) {
            throw new Error('FolderPicker must have an ID if initializing with jQuery.');
        }
        var selector = '#' + this.id;
        this._tb = new FolderPicker(selector, options);
    });
};


FolderPicker.selectView = treebeardSelectView;

module.exports = FolderPicker;

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
var $ = require('jquery');
var m = require('mithril');
var Treebeard = require('treebeard');


function _treebeardToggleCheck (item) {
    if (item.data.addon === 'figshare') {
        return false;
    }

    // if (item.data.path === '/') {
    //     return false;
    // }
    return true;
}

function _treebeardResolveToggle(item){
    if(item.data.addon === 'figshare') {
        return '';
    }

    return item.open ?
        m('i.icon-minus', ' '):
        m('i.icon-plus', ' ');
}

// Returns custom icons for OSF
function _treebeardResolveIcon(item){
    return item.open ?
        m('i.icon-folder-open-alt', ' '):
        m('i.icon-folder-close-alt', ' ');
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
    var tb = this;
    var setTempPicked = function () {
        this._tempPicked = item.id;
    };
    var templateChecked = m('input', {
        type:'radio',
        checked : 'checked',
        name: '#' + tb.options.divID + INPUT_NAME,
        value:item.id
    }, ' ');
    var templateUnchecked = m('input',{
        type: 'radio',
        onclick : setTempPicked.bind(tb),
        name: '#' + tb.options.divID + INPUT_NAME,
        value:item.id
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

function _treebeardColumnTitle() {
    return [
        {
            title: 'Folders',
            width : '75%',
            sort : false
        },
        {
            title : 'Select',
            width : '25%',
            sort : false
        }
    ];
}

function _treebeardResolveRows(item) {
    // this = treebeard;
    item.css = '';
    return [
        {
            data : 'name',  // Data field name
            folderIcons : true,
            filter : false,
            custom : _treebeardTitleColumn
        },
        {
            sortInclude : false,
            css : 'p-l-xs',
            custom : _treebeardSelectView
        }
    ];
}

function _treebeardOnload () {
    var tb = this;

    tb.options.folderIndex = 0;
    if (tb.options.folderPath) {
        tb.options.folderArray = tb.options.folderPath.split('/');
        if (tb.options.folderArray.length > 1) {
            tb.options.folderArray.splice(0, 1);
        }
    } else {
        tb.options.folderArray = [''];
    }

    if (tb.treeData.children[0].data.addon !== 'figshare') {
        tb.updateFolder(null, tb.treeData.children[0]);
    }
    tb.options.folderPickerOnload();
    // if (folderName != undefined) {
    //     if (folderName === 'None') {
    //         tb.options.folderPath = null;
    //     } else {
    //         if(folderPath) {
    //         }
    //         folderArray = folderName.trim().split('/');
    //         if (folderArray[folderArray.length - 1] === '') {
    //             folderArray.pop();
    //         }
    //         if (folderArray[0] === folderPath) {
    //             folderArray.shift();
    //         }
    //         tb.options.folderArray = folderArray;
    //     }
    //     for (var i = 0; i < tb.treeData.children.length; i++) {
    //         if (tb.treeData.children[i].data.addon !== 'figshare' && tb.treeData.children[i].data.name === folderArray[0]) {
    //             tb.updateFolder(null, tb.treeData.children[i]);
    //         }
    //     }
    //     tb.options.folderIndex = 1;
    // }
}

function _treebeardLazyLoadOnLoad(item) {
    var tb = this;

    for (var i = 0; i < item.children.length; i++) {
        if (item.children[i].data.addon === 'figshare'){
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
    columnTitles : _treebeardColumnTitle,
    resolveRows : _treebeardResolveRows,
    resolveIcon : _treebeardResolveIcon,
    togglecheck : _treebeardToggleCheck,
    resolveToggle : _treebeardResolveToggle,
    ondataload : _treebeardOnload,
    lazyLoadOnLoad : _treebeardLazyLoadOnLoad,
    // Disable uploads
    uploads: false,
    showFilter : false,
    resizeColumns : false,
    rowHeight : 35
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
    self.options.folderPath = opts.initialFolderPath;
    self.options.rootName = opts.rootName;
    
    var resolveRows = self.options.resolveRows;
    self.options.resolveRows = function(item){
	var res = resolveRows(item);
	var fn = res[1].custom.bind(this);
	res[1].custom = function(item){
	    var node = fn(item);
	    node.attrs.onchange = function(evt) {
		var id = $(this).val();
		var row = self.grid.find(id);		
		self.options.onPickFolder.call(self, evt, row);
	    };
	    return node;
	};
	return res;
    };

    // Start up the grid
    self.grid = new Treebeard(self.options).tbController;

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

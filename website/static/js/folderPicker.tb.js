/**
 * A simple folder picker plugin built on Treebeard.
 * Takes the same options as Treebeard and additionally requires an
 * `onChooseFolder` option (the callback executed when a folder is selected).
 *
 * Usage:
 *
 *     $('#myPicker').folderpicker({
 *         data: // Array of Treebeard-formatted data or URL to fetch data
 *         onPickFolder: function(evt, folder) {
 *             // do something with folder
 *         }
 *     });
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'treebeard'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['treebeard'], function() {
            global.FolderPicker = factory(jQuery, Treebeard);
            $script.done('folderPicker');
        });
    } else {
        global.FolderPicker = factory(jQuery, global.Treebeard);
    }
}(this, function($, Treebeard){
    'use strict';

    // Extend the default Treebeard name column
    FolderPicker.columnTitles = [];
    FolderPicker.columnTitles.push({
            title: 'Folders',
            width : '75%',
            sort : false
        },
        {
            title : 'Select',
            width : '25%',
            sort : false
    });

    FolderPicker.resolveRows = [];
    FolderPicker.resolveRows.push({
            data : 'name',  // Data field name
            folderIcons : true,
            filter : false,
            custom : _treebeardTitleColumn
        },
        {
            sortInclude : false,
            filter : false,
            custom : _treebeardSelectView
    });

    var INPUT_NAME = '-folder-select';
    //THIS NEEDS TO BE FIXED SO THAT ON CLICK IT OPENS THE FOLDER.
    function _treebeardTitleColumn (item, col) {
        return m('span',item.data.name);
    }

    /**
     * Returns the folder select button for a single row.
     */
    function _treebeardSelectView(item) {

        return m("input",{
            type:"radio",
            name:this.selector + INPUT_NAME,
            value:item.id,
            'onclick':function(){
                console.log("Proof of Concept: RADIO BUTTON CLICKED");
                //return item._fpChecked ? ' checked ': ' ';
            }
        }, " ")
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
            folderIcons : false,
            filter : false,
            custom : _treebeardTitleColumn
        });

        default_columns.push(
            {
            sortInclude : false,
            custom : _treebeardSelectView
        });

        return default_columns;
    }

    // Upon clicking the name of folder, toggle its collapsed state
    //function onClickName(evt, row, grid) {
    //    grid.toggleCollapse(row);
    //}

    // Default HGrid options
    var defaults = {
        columnTitles : _treebeardColumnTitle,
        resolveRows : _treebeardResolveRows,
        // Disable uploads
        uploads: false
        // Add listener that expands a folder upon clicking its name
        /*listeners: [
            {selector: '.' + HGrid.Html.nameClass, on: 'click',
            callback: onClickName}
        ],*/
    };

    function FolderPicker(selector, opts) {
        var self = this;
        self.selector = selector;
        self.checkedRowId = null;
        // Custom HGrid action to select a folder that uses the passed in
        // "onChooseFolder" callback
        if (!opts.onPickFolder) {
            throw 'FolderPicker must have the "onPickFolder" option defined';
        }
        self.options = $.extend({}, defaults, opts);
        self.options.filterOn = false;
        self.options.divID = selector.substring(1);

        //self.options.columnTitles = _treebeardTitleColumn();
        //self.options.resolveRows = _treebeardSelectView();

        // Start up the grid
        self.grid = Treebeard.run(self.options);
        // Set up listener for folder selection
        $(selector).on('change', 'input[name="' + self.selector + INPUT_NAME + '"]', function(evt) {
            var id = $(this).val();
            var row = self.grid.getByID(id);
            // Store checked state of rows so that it doesn't uncheck when HGrid is redrawn
            var oldRow = self.grid.getByID(self.checkedRowId);
            if (oldRow) {
                oldRow._fpChecked = false;
            }
            self.checkedRowId = row.id;
            row._fpChecked = true;
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
    // Export
    return FolderPicker;
}));

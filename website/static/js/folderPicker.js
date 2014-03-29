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
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'hgrid'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('hgrid', function() {
            global.FolderPicker = factory(jQuery, HGrid);
            $script.done('folderPicker');
        });
    } else {
        global.FolderPicker = factory(jQuery, global.HGrid);
    }
}(this, function($, HGrid){
    'use strict';

    // Extend the default HGrid name column
    FolderPicker.Col = {};
    FolderPicker.Col.Name = $.extend({}, HGrid.Col.Name);
    // Column title
    FolderPicker.Col.title = 'Folders';

    /**
     * Returns the folder select button for a single row.
     */
    function folderView() {
        var btn = {text: '<i class="icon-ok"></i>',
            action: 'chooseFolder', // Button triggers the custom "chooseFolder" action
            cssClass: 'btn btn-success btn-mini'};
        return HGrid.Fmt.button(btn);
    }

    // Custom selection button column.
    FolderPicker.Col.SelectFolder = {
        name: 'Select', folderView: folderView, width: 10
    };

    // Upon clicking the name of folder, toggle its collapsed state
    function onClickName(evt, row, grid) {
        grid.toggleCollapse(row);
    }

    // Default HGrid options
    var defaults = {
        columns: [FolderPicker.Col.Name,
                  FolderPicker.Col.SelectFolder
        ],
        // Disable uploads
        uploads: false, width: '100%', height: 300,
        // Add listener that expands a folder upon clicking its name
        listeners: [
            {selector: '.' + HGrid.Html.nameClass, on: 'click',
            callback: onClickName}
        ]
    };

    function FolderPicker(selector, opts) {
        var self = this;
        self.selector = selector;
        // Custom HGrid action to select a folder that uses the passed in
        // "onChooseFolder" callback
        if (!opts.onPickFolder) {
            throw 'FolderPicker must have the "onPickFolder" option defined';
        }
        HGrid.Actions.chooseFolder = {
            on: 'click', callback: opts.onPickFolder
        };
        self.options = $.extend({}, defaults, opts);
        // Start up the grid
        self.grid = new HGrid(selector, self.options);
    }

    // Augment jQuery
    $.fn.folderpicker = function(options) {
        this.each(function() {
            // HGrid must take an ID as a selector if using as a jQuery plugin
            if (!this.id) { throw 'FolderPicker must have an ID if initializing with jQuery.'; }
            var selector = '#' + this.id;
            return new FolderPicker(selector, options);
        });
    };
    // Export
    return FolderPicker;
}));

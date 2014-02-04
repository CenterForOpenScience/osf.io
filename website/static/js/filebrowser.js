/**
 * Module to render the consolidated files view. Reads addon configurrations and
 * initializes an HGrid.
 */
this.FileBrowser = (function($, HGrid, bootbox) {
    var tpl = HGrid.Fmt.tpl;

    // Can't use microtemplate because microtemplate escapes html
    // Necessary for rendering, e.g. the github branch picker
    HGrid.Col.Name.folderView = function(item) {
        return HGrid.Html.folderIcon + item.name;
    };

    // OSF-specific HGrid options common to all addons
    baseOptions = {
        columns: [
            HGrid.Col.Name,
            HGrid.Col.ActionButtons
        ],
        width: '100%',
        fetchUrl: function(row) {
            return row.urls.fetch;
        },
        downloadUrl: function(row) {
            return row.urls.download;
        },
        deleteUrl: function(row) {
            return row.urls.delete;
        },
        onClickDelete: function(evt, row) {
            console.log(this);
            var self = this;
            // TODO: This text should be configurable by addon devs
            var msg = tpl('Are you sure you want to delete "{{name}}"?', row);
            var ajaxOptions = {
                error: function() {
                    bootbox.alert('There was a problem deleting your file. Please try again later.');
                },
                success: function() {
                    bootbox.alert('File deleted.');
                }
            };
            bootbox.confirm(msg, function(confirmed) {
                if (confirmed) {
                    // Send request to delete file.
                    self.removeItem(row.id);
                    self.deleteFile(row, ajaxOptions);
                }
            });
            return this;
        },
        deleteMethod: 'delete',
        uploads: true,
        uploadUrl: function(row) {
            return row.urls.upload;
        },
        uploadMethod: 'post',
        listeners: [
            // Go to file's detail page if name is clicked
            {
                on: 'click',
                selector: '.hg-item-content',
                callback: function(evt, row, grid) {
                    if (row) {
                        var viewUrl = grid.getByID(row.id).urls.view;
                        if (viewUrl) {
                            window.location.href = viewUrl;
                        }
                    }
                }
            }
        ]
    };

    // Public API
    function FileBrowser(selector, options) {
        this.selector = selector;
        this.options = $.extend({}, baseOptions, options);
        this.grid = null; // Set by _initGrid
        this.init();
    }
    // Addon config registry
    FileBrowser.cfg = {};

    FileBrowser.prototype = {
        constructor: FileBrowser,
        init: function() {
            this._registerListeners()
                ._initGrid();
        },
        _registerListeners: function() {
            for (var addon in FileBrowser.cfg) {
                var listeners = FileBrowser.cfg[addon].listeners;
                // Add each listener to the hgrid options
                for (var i = 0, listener; listener = listeners[i]; i++) {
                    this.options.listeners.push(listener);
                }
            }
            return this;
        },
        // Create the Hgrid once all addons have been configured
        _initGrid: function() {
            this.grid = new HGrid(this.selector, this.options);
            return this;
        }
    };

    return FileBrowser;

})(jQuery, HGrid, bootbox);

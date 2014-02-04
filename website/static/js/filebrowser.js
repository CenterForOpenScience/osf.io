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

    HGrid.Col.ActionButtons.itemView = function() {
      var buttonDefs = [{
          text: '<i class="icon-download-alt icon-white"></i>',
          action: 'download',
          cssClass: 'btn btn-success btn-mini'
      }, {
          text: '<i class="icon-trash icon-white"></i>',
          action: 'delete',
          cssClass: 'btn btn-danger btn-mini'
      }];
      return HGrid.Fmt.buttons(buttonDefs);
    };

    HGrid.Col.ActionButtons.folderView = function() {
        var buttonDefs = [];
        if (this.options.uploads) {
          buttonDefs.push({
            text: '<i class="icon-cloud-upload icon-white"></i>',
            action: 'upload',
            cssClass: 'btn btn-primary btn-mini'
          });
        }
        if (buttonDefs) {
          return HGrid.Fmt.buttons(buttonDefs);
        }
        return '';
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
                }
            };
            bootbox.confirm(msg, function(confirmed) {
                if (confirmed) {
                    self.removeItem(row.id);
                    // Send request to delete file.
                    self.deleteFile(row, ajaxOptions);
                }
            });
            return this;
        },
        deleteMethod: 'delete',
        uploads: true,
        uploadUrl: function(row) {
            var cfgFunc = FileBrowser.getCfg(row, 'uploadUrl');
            if (cfgFunc) {
                return cfgFunc.call(this, row);
            }
            return row.urls.upload;
        },
        uploadAdded: function(file, row) {
            var parent = this.getByID(row.parentID);
            row.addon = parent.addon;
            var cfgFunc = FileBrowser.getCfg(row, 'uploadAdded');
            if (cfgFunc) {
                return cfgFunc.call(this, file, row);
            }
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

    FileBrowser.getCfg = function(row, key) {
        return this.cfg[row.addon][key];
    };

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

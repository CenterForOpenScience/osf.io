/**
 * Module to render the consolidated files view. Reads addon configurrations and
 * initializes an HGrid.
 */
this.FileBrowser = (function($, HGrid, bootbox) {
    var tpl = HGrid.Fmt.tpl;

    HGrid.Col.ActionButtons.itemView = function(row) {
      var buttonDefs = [{
          text: '<i class="icon-download-alt icon-white"></i>',
          action: 'download',
          cssClass: 'btn btn-primary btn-mini'
      }, {
          text: '&nbsp;<i class="icon-remove"></i>',
          action: 'delete',
          cssClass: 'btn btn-link btn-mini btn-delete'
      }];
      return HGrid.Fmt.buttons(buttonDefs);
    };

    HGrid.Col.ActionButtons.folderView = function(row) {
        var buttonDefs = [];
        if (this.options.uploads) {
          buttonDefs.push({
            text: '<i class="icon-upload"></i>',
            action: 'upload',
            cssClass: 'btn btn-default btn-mini'
          });
        }
        if (buttonDefs) {
          return HGrid.Fmt.buttons(buttonDefs);
        }
        return '';
    };

    HGrid.Actions.delete = {
        on: 'click',
        callback: function(evt, item) {
            var self = this;
            $(evt.target).inlineConfirmation({
                confirmCallback: function() {
                    self.deleteFile(item);
                }
            });
        }
    };


    // OSF-specific HGrid options common to all addons
    baseOptions = {
        columns: [
            HGrid.Col.Name,
            HGrid.Col.ActionButtons
        ],
        width: '100%',
        height: 600,
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
        uploadMethod: function(file, row) {
            var cfgFunc = FileBrowser.getCfg(row, 'uploadMethod');
            if (cfgFunc) {
                return cfgFunc.call(this, file, row);
            }
            return 'post';
        },
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
        ],
        init: function() {
            var self = this;
            // Expand all first level items
            this.getData().forEach(function(item) {self.expandItem(item);});
        }
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
        if (row && row.addon && this.cfg[row.addon]){
            return this.cfg[row.addon][key];
        }
        return undefined;
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
                if (listeners){
                    // Add each listener to the hgrid options
                    for (var i = 0, listener; listener = listeners[i]; i++) {
                        this.options.listeners.push(listener);
                    }
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

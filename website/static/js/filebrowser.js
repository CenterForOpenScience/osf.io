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

    // OSF-specific HGrid options common to all addons
    baseOptions = {
        /*jshint unused: false */
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
            var $elem = $(evt.target);
            // Show inline confirm
            // TODO: Make inline confirmation more reuseable
            $elem.closest('[data-hg-action="delete"]')
                .html('Are you sure? <a class="unconfirm" data-target="">No</a> / <a class="confirm" data-target="">Yes</a>');
            return this;
        },
        deleteMethod: 'delete',
        uploads: true,
        uploadUrl: function(row) {
            var cfgOption = resolveCfgOption.call(this, row, 'uploadUrl', [row]);
            return cfgOption || row.urls.upload;
        },
        uploadAdded: function(file, row) {
            var parent = this.getByID(row.parentID);
            row.addon = parent.addon;
            var cfgOption = resolveCfgOption.call(this, row, 'uploadAdded', [file, row]);
            return cfgOption || null;
        },
        uploadMethod: function(row) {
            var cfgOption = resolveCfgOption.call(this, row, 'uploadMethod', [row]);
            return cfgOption || 'post';
        },
        uploadSending: function(file, row, xhr, formData) {
            var cfgOption = resolveCfgOption.call(this, row, 'uploadSending', [file, row, xhr, formData]);
            return cfgOption || null;
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
            },
            {
                on: 'click', selector: '.confirm',
                callback: function(evt, row, grid) {
                    if (row) {
                        grid.deleteFile(row, {
                            error: function() {
                                // TODO: This text should be configurable by addon devs
                                bootbox.error('Could not delete ' + row.name + '. Please try again later.');
                            }
                        });
                    }
                }
            },
            {
                on: 'click', selector: '.unconfirm',
                callback: function(evt, row, grid) {
                    if (row) {
                        // restore row html
                        grid.updateItem(row);
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

    // Gets a FileBrowser config option if it is defined by an addon dev.
    // Calls it with `args` if it's a function otherwise returns the value.
    // If the config option is not defined, return null
    function resolveCfgOption(row, option, args) {
        var self = this;
        var prop = FileBrowser.getCfg(row, option);
        if (prop) {
            return typeof prop === 'function' ? prop.apply(self, args) : prop;
        } else {
            return null;
        }
    }

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

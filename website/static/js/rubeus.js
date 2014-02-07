/**
 * Module to render the consolidated files view. Reads addon configurrations and
 * initializes an HGrid.
 */
this.Rubeus = (function($, HGrid, bootbox) {

    /////////////////////////
    // HGrid configuration //
    /////////////////////////

    var tpl = HGrid.Fmt.tpl;

    // Can't use microtemplate because microtemplate escapes html
    // Necessary for rendering, e.g. the github branch picker
    HGrid.Col.Name.folderView = function(item) {
        var tpl = '';
        if (item.iconUrl)
            tpl += '<img class="hg-addon-icon" src="' + item.iconUrl + '">';
        else
            tpl += HGrid.Html.folderIcon;
        tpl += '<span class="hg-folder-text">' + item.name + '</span>';
        if(item.extra)
            tpl += '<span class="hg-extras">' + item.extra + '</span>';
        return tpl;
    };

    HGrid.Col.Name.itemView = function(item) {
        var ext = item.name.split('.').pop().toLowerCase();
        return HGrid.Extensions.indexOf(ext) == -1 ?
            HGrid.Html.fileIcon + item.name:
            HGrid.ExtensionSkeleton.replace('{{ext}}', ext) + item.name;
    };

    HGrid.Col.ActionButtons.itemView = function(item) {
      var buttonDefs = [{
          text: '<i class="icon-download-alt icon-white"></i>',
          action: 'download',
          cssClass: 'btn btn-primary btn-mini'
      }];
      if (item.permissions && item.permissions.edit) {
          buttonDefs.push({
              text: '&nbsp;<i class="icon-remove"></i>',
              action: 'delete',
              cssClass: 'btn btn-link btn-mini btn-delete'
          });
      }
      return HGrid.Fmt.buttons(buttonDefs);
    };

    HGrid.Col.ActionButtons.width = 15;
    HGrid.Col.ActionButtons.folderView = function(row) {
        // var buttonDefs = [];
        // if (this.options.uploads &&
        //     row.urls.upload
        //     (row.permissions && row.permissions.edit)) {
        //     buttonDefs.push({
        //         text: '<i class="icon-upload"></i>',
        //         action: 'upload',
        //         cssClass: 'btn btn-default btn-mini'
        //     });
        // }
        // if (buttonDefs) {
        //     return HGrid.Fmt.buttons(buttonDefs);
        // }
        return '';
    };

    // Custom status column
    HGrid.Col.Status = {
        text: 'Status',
        folderView: '<span data-status></span>',
        itemView: '<span data-status></span>',
        width: 50
    };
    HGrid.Html.statusSelector = '[data-status]';

    /**
     * Changes the html in the status column.
     */
    HGrid.prototype.changeStatus = function(row, html, fadeAfter) {
        var rowElem = this.getRowElement(row.id);
        var $status = $(rowElem).find(HGrid.Html.statusSelector);
        $status.html(html);
        if (fadeAfter) {
            setTimeout(function() {
                $status.fadeOut('slow');
            }, fadeAfter);
        }
        return $status;
    };

    // TODO: This should be configurable by addon devs
    var status = {
        FETCH_SUCCESS: '',
        FETCH_START: '<span class="text-muted">Fetching contents. . .</span>',
        FETCH_ERROR: '<span class="text-info">Could not retrieve data. Please refresh the page and try again.</span>',

        UPLOAD_SUCCESS: '<span class="text-success">Successfully uploaded</span>',
        DELETING: function(row) {
            return '<span class="text-muted">Deleting "' + row.name + '"</span>';
        },
        DELETED: function(row) {
            return '<span class="text-warning">Successfully deleted "' + row.name + '"</span>';
        },
        UPLOAD_ERROR: function(msg) {
            return '<span class="text-danger">' + msg + '</span>';
        },
        UPLOAD_PROGRESS: function(progress) {
            return '<span class="text-info">' + Math.floor(progress) + '%</span>';
        }
    };

    ////////////////////////
    // Listener callbacks //
    ////////////////////////

    function onConfirmDelete(evt, row, grid) {
        if (row) {
            var rowCopy = $.extend({}, row);
            // Show "Deleting..." message in parent folder's status column
            var parent = grid.getByID(rowCopy.parentID);
            grid.changeStatus(parent, status.DELETING(rowCopy));
            grid.deleteFile(row, {
                error: function() {
                    // TODO: This text should be configurable by addon devs
                    bootbox.error('Could not delete ' + row.name + '. Please try again later.');
                },
                success: function() {
                    grid.getDataView().updateItem(parent.id, parent);
                    grid.removeItem(rowCopy.id);
                    // Show 'Successfully deleted' in folder's status column
                    grid.changeStatus(parent, status.DELETED(rowCopy), 2000);
                }
            });
        }
    }

    function onClickName(evt, row, grid) {
        if (row) {
            var viewUrl = grid.getByID(row.id).urls.view;
            if (viewUrl) {
                window.location.href = viewUrl;
            }
            if (row.kind === HGrid.FOLDER && row.depth !== 0) {
                grid.toggleCollapse(row);
            }
        }
    }

    ///////////////////
    // HGrid options //
    ///////////////////

    // OSF-specific HGrid options common to all addons
    baseOptions = {
        /*jshint unused: false */
        columns: [
            HGrid.Col.Name,
            HGrid.Col.ActionButtons,
            HGrid.Col.Status
        ],
        width: '100%',
        height: 500,
        fetchUrl: function(row) {
            return row.urls.fetch;
        },
        fetchSuccess: function(data, row) {
            this.changeStatus(row, status.FETCH_SUCCESS);
        },
        fetchError: function(error, row) {
            this.changeStatus(row, status.FETCH_ERROR);
        },
        fetchStart: function(row) {
            this.changeStatus(row, status.FETCH_START);
        },
        uploadProgress: function(file, progress, bytesSent, row) {
            this.changeStatus(row, status.UPLOAD_PROGRESS(progress));
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
        maxFilesize: function(row) {
            var cfgOption = resolveCfgOption.call(this, row, 'maxFilesize', [row]);
            return cfgOption || 128;
        },
        uploadUrl: function(row) {
            var cfgOption = resolveCfgOption.call(this, row, 'uploadUrl', [row]);
            return cfgOption || row.urls.upload;
        },

        uploadAdded: function(file, row, folder) {
            // Need to set the added row's addon for other callbacks to work
            var parent = this.getByID(row.parentID);
            row.addon = parent.addon;
            // expand the folder
            this.expandItem(folder);
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
        uploadError: function(file, message, item, folder) {
            // FIXME: can't use change status, because the folder item is updated
            // on complete, which replaces the html row element
            // for now, use bootbox
            bootbox.alert(message);
        },
        uploadSuccess: function(file, row, data) {
            // Update the row with the returned server data
            // This is necessary for the download and delete button to work.
            $.extend(row, data);
            this.updateItem(row);
            this.changeStatus(row, status.UPLOAD_SUCCESS, 2000);
            var cfgOption = resolveCfgOption.call(this, row, 'uploadSuccess', [file, row, data]);
            return cfgOption || null;
        },
        // TODO: Set parallel uploads to 1 for now until git collision issue is fixed
        dropzoneOptions: {
            parallelUploads: 1
        },
        listeners: [
            // Go to file's detail page if name is clicked
            {
                on: 'click',
                selector: '.' + HGrid.Html.nameClass,
                callback: onClickName
            }, {
                on: 'click',
                selector: '.confirm',
                callback: onConfirmDelete
            }, {
                on: 'click',
                selector: '.unconfirm',
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
            this.getData().forEach(function(item) {
                self.expandItem(item);
            });
        }
    };

    ///////////////////////
    // Rubeus Public API //
    ///////////////////////

    function Rubeus(selector, options) {
        this.selector = selector;
        this.options = $.extend({}, baseOptions, options);
        this.grid = null; // Set by _initGrid
        this.init();
    }
    // Addon config registry
    Rubeus.cfg = {};

    Rubeus.getCfg = function(row, key) {
        if (row && row.addon && this.cfg[row.addon]) {
            return this.cfg[row.addon][key];
        }
        return undefined;
    };

    // Gets a Rubeus config option if it is defined by an addon dev.
    // Calls it with `args` if it's a function otherwise returns the value.
    // If the config option is not defined, return null
    function resolveCfgOption(row, option, args) {
        var self = this;
        var prop = Rubeus.getCfg(row, option);
        if (prop) {
            return typeof prop === 'function' ? prop.apply(self, args) : prop;
        } else {
            return null;
        }
    }

    Rubeus.prototype = {
        constructor: Rubeus,
        init: function() {
            this._registerListeners()
                ._initGrid();
        },
        _registerListeners: function() {
            for (var addon in Rubeus.cfg) {
                var listeners = Rubeus.cfg[addon].listeners;
                if (listeners) {
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

    return Rubeus;

})(jQuery, HGrid, bootbox);

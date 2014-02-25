/**
 * Module to render the consolidated files view. Reads addon configurations and
 * initializes an HGrid.
 */
this.Rubeus = (function($, HGrid, bootbox, window) {

    /////////////////////////
    // HGrid configuration //
    /////////////////////////

    // Custom folder icon indicating private component
    HGrid.Html.folderIconPrivate = '<img class="hg-addon-icon" src="/static/img/hgrid/fatcowicons/folder_delete.png">';
    // Override Name column folder view to allow for extra widgets, e.g. github branch picker
    HGrid.Col.Name.folderView = function(item) {
        var icon, opening, cssClass;
        if (item.iconUrl) {
            // use item's icon based on filetype
            icon = '<img class="hg-addon-icon" src="' + item.iconUrl + '">';
            cssClass = '';
        } else
            if (!item.permissions.view) {
                icon = HGrid.Html.folderIconPrivate;
                cssClass = 'hg-folder-private';
            } else {
                icon = HGrid.Html.folderIcon;
                cssClass = 'hg-folder-public';
            }
        opening = '<span class="hg-folder-text ' + cssClass + '">';
        var closing = '</span>';
        html = [icon, opening, item.name, closing].join('');
        if(item.extra) {
            html += '<span class="hg-extras">' + item.extra + '</span>';
        }
        return html;
    };

    HGrid.Col.Name.showExpander = function(row) {
        return row.kind === HGrid.FOLDER && row.permissions.view;
    };

    HGrid.Col.Name.itemView = function(item) {
        var ext = item.name.split('.').pop().toLowerCase();
        return HGrid.Extensions.indexOf(ext) === -1 ?
            HGrid.Html.fileIcon + item.name:
            HGrid.ExtensionSkeleton.replace('{{ext}}', ext) + item.name;
    };

    HGrid.Col.ActionButtons.itemView = function(item) {
	var buttonDefs = [];
	if(item.permisssions.download !== false){
	    buttonDefs.push{
		text: '<i class="icon-download-alt icon-white"></i>',
		action: 'download',
		cssClass: 'btn btn-primary btn-mini'
	    };
	}
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
        var buttonDefs = [];
        if (this.options.uploads && row.urls.upload &&
                (row.permissions && row.permissions.edit)) {
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


    // Custom status column
    HGrid.Col.Status = {
        text: 'Status',
        folderView: '<span data-status></span>',
        itemView: '<span data-status></span>',
        width: 50
    };
    HGrid.Html.statusSelector = '[data-status]';

    /**
     * Get the status message from the addon, if any.
     */
     function getStatusCfg(addon, whichStatus, extra) {
        if (addon && Rubeus.cfg[addon] && Rubeus.cfg[addon][whichStatus]) {
            if (typeof(Rubeus.cfg[addon][whichStatus]) === 'function') {
                return Rubeus.cfg[addon][whichStatus](extra);
            }
            return Rubeus.cfg[addon][whichStatus];
        }
        if (typeof(default_status[whichStatus]) === 'function') {
            return default_status[whichStatus](extra);
        }
        return default_status[whichStatus];
     }

/**
     * Changes the html in the status column.
     */
    HGrid.prototype.changeStatus = function(row, html, extra, fadeAfter) {
        var rowElem = this.getRowElement(row.id);
        var $status = $(rowElem).find(HGrid.Html.statusSelector);
        $status.html(getStatusCfg(row.addon, html, extra));
        if (fadeAfter) {
            setTimeout(function() {
                $status.fadeOut('slow');
            }, fadeAfter);
        }
        return $status;
    };

    var default_status = {
        FETCH_SUCCESS: '',
        FETCH_START: '<span class="text-muted">Fetching contents. . .</span>',
        FETCH_ERROR: '<span class="text-info">Could not retrieve data. Please refresh the page and try again.</span>',

        UPLOAD_SUCCESS: '<span class="text-success">Successfully uploaded</span>',
        NO_CHANGES: '<span class="text-info">No changes made from previous version. Removing duplicate row. . .</span>',
        UPDATED: '<span class="text-info">Existing file updated. Removing duplicate row. . .</span>',
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

    var statusType = {
        FETCH_SUCCESS: 'FETCH_SUCCESS',
        FETCH_START: 'FETCH_START',
        FETCH_ERROR: 'FETCH_ERROR',
        UPLOAD_SUCCESS: 'UPLOAD_SUCCESS',
        NO_CHANGES: 'NO_CHANGES',
        UPDATED: 'UPDATED',
        DELETING: 'DELETING',
        DELETED: 'DELETED',
        UPLOAD_ERROR: 'UPLOAD_ERROR',
        UPLOAD_PROGRESS: 'UPLOAD_PROGRESS'
    };

    Rubeus.Status = statusType
    ////////////////////////
    // Listener callbacks //
    ////////////////////////

    function onConfirmDelete(row, grid) {
        if (row) {
            var rowCopy = $.extend({}, row);
            // Show "Deleting..." message in parent folder's status column
            var parent = grid.getByID(rowCopy.parentID);
            grid.changeStatus(row, statusType.DELETING, rowCopy);
            grid.deleteFile(row, {
                error: function() {
                    // TODO: This text should be configurable by addon devs
                    bootbox.error('Could not delete ' + row.name + '. Please try again later.');
                },
                success: function() {
                    grid.getDataView().updateItem(parent.id, parent);
                    // Show 'Successfully deleted' in folder's status column
                    grid.changeStatus(row, statusType.DELETED, rowCopy);
                    setTimeout(function(){
                        grid.removeItem(rowCopy.id);
                    }, 1000);
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
            return row.urls.fetch || null;
        },
        fetchSuccess: function(data, row) {
            this.changeStatus(row, statusType.FETCH_SUCCESS);
        },
        fetchError: function(error, row) {
            this.changeStatus(row, statusType.FETCH_ERROR);
        },
        fetchStart: function(row) {
            this.changeStatus(row, statusType.FETCH_START);
        },
        uploadProgress: function(file, progress, bytesSent, row) {
            this.changeStatus(row, statusType.UPLOAD_PROGRESS, progress);
        },
        downloadUrl: function(row) {
            return row.urls.download;
        },
        deleteUrl: function(row) {
            return row.urls.delete;
        },
        onClickDelete: function(evt, row) {
            var self = this;
            var $elem = $(evt.target);
            bootbox.confirm({
                message: '<strong>NOTE</strong>: This action is irreversible.',
                title: 'Delete <em>' + row.name + '</em>?',
                callback: function(result) {
                    if (result) {
                        onConfirmDelete(row, self);
                    }
                }
            });
            return this;
        },
        canUpload: function(folder) {
            return folder.permissions.edit;
        },
        deleteMethod: 'delete',
        uploads: true,
        maxFilesize: function(row) {
            return row.accept? (row.accept.maxSize || 128) : 128;
        },
        // acceptedFiles: function(row) {
        //     return row.accept.acceptedFiles || null;
        // },
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
            // If file hasn't changed, remove the duplicate item
            // TODO: shows status in parent for now because the duplicate item
            // is removed and we don't have access to the original row for the file
            var self = this;
            if (data.actionTaken === null) {
                self.changeStatus(row, statusType.NO_CHANGES);
                setTimeout(function() {
                    $(self.getRowElement(row)).fadeOut(500, function() {
                        self.removeItem(row.id);
                    });
                }, 2000);
            } else if (data.actionTaken === 'file_updated') {
                self.changeStatus(row, statusType.UPDATED);
                setTimeout(function() {
                    $(self.getRowElement(row)).fadeOut(500, function() {
                        self.removeItem(row.id);
                    });
                }, 2000);
            } else{
                // Update the row with the returned server data
                // This is necessary for the download and delete button to work.
                $.extend(row, data);
                this.updateItem(row);
                this.changeStatus(row, statusType.UPLOAD_SUCCESS, null, 2000);
            }
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

    function getCfg(row, key) {
        if (row && row.addon && Rubeus.cfg[row.addon]) {
            return Rubeus.cfg[row.addon][key];
        }
        return undefined;
    }

    // Gets a Rubeus config option if it is defined by an addon dev.
    // Calls it with `args` if it's a function otherwise returns the value.
    // If the config option is not defined, return null
    function resolveCfgOption(row, option, args) {
        var self = this;
        var prop = getCfg(row, option);
        if (prop) {
            return typeof prop === 'function' ? prop.apply(self, args) : prop;
        } else {
            return null;
        }
    }

    Rubeus.prototype = {
        constructor: Rubeus,
        init: function() {
            var self = this;
            this._registerListeners()
                ._initGrid();
            // Show alert if user tries to leave page before upload is finished.
            $(window).on('beforeunload', function() {
                if (self.grid.dropzone && self.grid.dropzone.getUploadingFiles().length) {
                    return 'Uploads(s) still in progress. Are you sure you want to leave this page?';
                }
            });
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

})(jQuery, HGrid, bootbox, window);

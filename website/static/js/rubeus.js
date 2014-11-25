/**
 * An OSF-flavored wrapper around HGrid.
 *
 * Module to render the consolidated files view. Reads addon configurations and
 * initializes an HGrid.
 */
(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'hgrid', 'js/dropzone-patch', 'bootstrap'], factory);
    } else if (typeof $script === 'function' ){
        $script.ready(['dropzone', 'dropzone-patch', 'hgrid'], function() {
            global.Rubeus = factory(jQuery, global.HGrid);
            $script.done('rubeus');
        });
    }else {
        global.Rubeus = factory(jQuery, global.HGrid);
    }
}(this, function($, HGrid){
    /////////////////////////
    // HGrid configuration //
    /////////////////////////

    var escapeWhitespace = function(value) {
        return value.replace(/\s/g, '&nbsp;');
    };

    Rubeus.Html = $.extend({}, HGrid.Html);
    // Custom folder icon indicating private component
    Rubeus.Html.folderIconPrivate = '<img class="hg-icon hg-addon-icon" src="/static/img/hgrid/fatcowicons/folder_delete.png">';
    // Folder icon for pointers/links
    Rubeus.Html.folderIconPointer = '<i class="icon-link"></i>';
    // Class for folder name
    Rubeus.Html.folderTextClass = 'hg-folder-text';

    // Override Name column folder view to allow for extra widgets, e.g. github branch picker
    Rubeus.Col = {};
    // Copy default name column from HGrid
    Rubeus.Col.Name = $.extend({}, HGrid.Col.Name);
    Rubeus.Col.Name.folderView = function(item) {
        var icon, opening, cssClass;
        if (item.iconUrl) {
            // use item's icon based on filetype
            icon = '<img class="hg-addon-icon" src="' + item.iconUrl + '">';
            cssClass = '';
        } else {
            if (!item.permissions.view) {
                icon = Rubeus.Html.folderIconPrivate;
                cssClass = 'hg-folder-private';
            } else if (item.isPointer) {
                icon = Rubeus.Html.folderIconPointer;
                cssClass = 'hg-folder-pointer';
            } else {
                icon = HGrid.Html.folderIcon;
                cssClass = 'hg-folder-public';
            }
        }
        opening = '<span class="' + Rubeus.Html.folderTextClass + ' ' + cssClass + '">';
        var closing = '</span>';
        html = [opening, icon, '&nbsp;', escapeWhitespace(item.name), closing].join('');
        if(item.extra) {
            html += '<span class="hg-extras">' + item.extra + '</span>';
        }
        return html;
    };

    Rubeus.Col.Name.showExpander = function(row) {
        var isTopLevel = row.parentID === HGrid.ROOT_ID;
        return row.kind === HGrid.FOLDER && row.permissions.view && !isTopLevel;
    };

    Rubeus.Col.Name.itemView = function(item) {
        var tooltipMarkup = genTooltipMarkup('View file');
        icon = Rubeus.getIcon(item);
        return [icon, '<span ' + tooltipMarkup + ' >&nbsp;', escapeWhitespace(item.name), '</span>'].join('');
    };

    Rubeus.Sort = {
        defaultColumn: 'name',
        defaultAsc: true
    };

    /**
     * Generate the markup necessary for adding a tooltip to an element.
     */
    function genTooltipMarkup(title, maxLength) {
        var max = maxLength || 30;
        // Truncate title if necessary
        var cleanTitle;
        if (title.length >= max) {
            cleanTitle = title.slice(0, max) + '...';
        } else {
            cleanTitle = title;
        }
        return ' title="' + cleanTitle + '" data-placement="right" ' +
                                'data-toggle="tooltip" ';
    }

    Rubeus.Col.ActionButtons = $.extend({}, HGrid.Col.ActionButtons);
    Rubeus.Col.ActionButtons.itemView = function(item) {
    var buttonDefs = [];
    var tooltipMarkup = '';
    if(item.permissions){
        if(item.permissions.download !== false){
            tooltipMarkup = genTooltipMarkup('Download');
            buttonDefs.push({
                text: '<i class="icon-download-alt icon-white" title=""></i>',
                action: 'download',
                cssClass: 'btn btn-primary btn-mini',
                attributes: tooltipMarkup
            });
        }
        if (item.permissions.edit) {
            tooltipMarkup = genTooltipMarkup('Remove');
            buttonDefs.push({
                text: '&nbsp;<i class="icon-remove" title=""></i>',
                action: 'delete',
                cssClass: 'btn btn-link btn-mini btn-delete',
                attributes: tooltipMarkup
            });
        }
    }
    if (item.buttons) {
        item.buttons.forEach(function(button) {
            buttonDefs.push({
                text: button.text,
                action: button.action,
                cssClass: 'btn btn-primary btn-mini',
                attributes: button.attributes
            });
        });
    }
    return ['<span class="rubeus-buttons">', HGrid.Fmt.buttons(buttonDefs),
                '</span><span data-status></span>'].join('');
    };

    /** Remove the 'Project: ' text from the beginning of a folder name. */
    function trimFolderName(name) {
        return name.slice(name.indexOf(':') + 1).trim();
    }

    Rubeus.Col.ActionButtons.name = 'Actions';
    Rubeus.Col.ActionButtons.width = 70;
    Rubeus.Col.ActionButtons.folderView = function(row) {
        var buttonDefs = [];
        var tooltipMarkup = genTooltipMarkup('Upload');
        if (this.options.uploads && row.urls.upload &&
                (row.permissions && row.permissions.edit)) {
            buttonDefs.push({
                text: '<i class="icon-upload" title=""></i>',
                action: 'upload',
                cssClass: 'btn btn-default btn-mini',
                attributes: tooltipMarkup
            });
        }
        if (row.buttons) {
            row.buttons.forEach(function(button) {
                buttonDefs.push({
                    text: button.text,
                    action: button.action,
                    cssClass: 'btn btn-primary btn-mini',
                    attributes: button.attributes
                });
            });
        }
        if (buttonDefs) {
            return ['<span class="' + Rubeus.buttonContainer + '">', HGrid.Fmt.buttons(buttonDefs),
                '</span><span data-status></span>'].join('');
        }
        return '';
    };

    Rubeus.Utils = {};

    /**
     * Check whether newly uploaded item was added or updated. This is
     * a hack that's necessary for services with indirect uploads (S3,
     * OSF Storage) that don't tell us whether the file was added or
     * updated.
     */
    Rubeus.Utils.itemUpdated = function(item, parent) {
        var siblings = parent._node.children;
        var matchCount = 0;
        for (var i=0; i<siblings.length; i++) {
            if (item.name === siblings[i].data.name) {
                matchCount += 1;
                // If `item` is being updated, it will appear twice in the grid:
                // once for the original version, and a second time for the
                // temporary item added on drop.
                if (matchCount >= 2) {
                    return true;
                }
            }
        }
        return false;
    };

    /**
     * Get the status message from the addon if defined, otherwise use the default message.
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

    HGrid.prototype.showButtons = function(row) {
        var $rowElem;
        try {
            $rowElem = $(this.getRowElement(row.id));
        } catch(error) {
            return this;
        }
        var $buttons = $rowElem.find('.' + Rubeus.buttonContainer);
        $buttons.show();
        return this;
    };

    HGrid.prototype.hideButtons = function(row) {
        var $rowElem;
        try {
            $rowElem = $(this.getRowElement(row.id));
        } catch (error) {
            return this;
        }
        var $buttons = $rowElem.find('.rubeus-buttons');
        $buttons.hide();
        return this;
    };

    HGrid.prototype.delayRemoveRow = function(row) {
        var self = this;
        setTimeout(function() {
            try {
                $(self.getRowElement(row)).fadeOut(500, function() {
                    self.removeItem(row.id);
                });
            } catch (error) {
                self.removeItem(row.id);
            }
        }, 2000);
    };

    /**
     * Changes the html in the status column.
     */
    HGrid.prototype.changeStatus = function(row, html, extra, fadeAfter, callback) {
        var $rowElem, $status;
        try {
            // Raises TypeError if row's HTML is not rendered.
            $rowElem = $(this.getRowElement(row.id));
        } catch (err) {
            return;
        }
        $status = $rowElem.find(Rubeus.statusSelector);
        this.hideButtons(row);
        $status.html(getStatusCfg(row.addon, html, extra));
        if (fadeAfter) {
            setTimeout(function() {
                $status.fadeOut('slow', function() {callback(row);});
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
        },
        RELEASING_STUDY: '<span class="text-info">Releasing Study. . .</span>'
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
        UPLOAD_PROGRESS: 'UPLOAD_PROGRESS',
        RELEASING_STUDY: 'RELEASING_STUDY'
    };

    Rubeus.Status = statusType;
    Rubeus.buttonContainer = 'rubeus-buttons';
    Rubeus.statusSelector = '[data-status]';
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
        }
    }

    function onClickFolderName(evt, row, grid) {
        onClickName(evt, row, grid);
        if (row && row.kind === HGrid.FOLDER && row.depth !== 0) {
            grid.toggleCollapse(row);
        }
    }

    // Custom download count column
    var DownloadCount = {
        name: 'Downloads',
        itemView: '{{ downloads }}',
        folderView: '',
        width: 20
    };

    ///////////////////
    // HGrid options //
    ///////////////////

    // OSF-specific HGrid options common to all addons
    baseOptions = {
        /*jshint unused: false */
        columns: [
            Rubeus.Col.Name,
            Rubeus.Col.ActionButtons,
            DownloadCount
        ],
        width: '100%',
        height: 900,
        ajaxOptions: {
            cache: false  // Prevent caching in IE
        },
        preprocessFilename: function(filename) {
            // // Render repeated whitespace characters appropriately
            // filename = filename.replace(/\s/g, '&nbsp;');
            return $('<div>').text(filename).html();
        },
        fetchUrl: function(row) {
            return row.urls.fetch || null;
        },
        fetchSuccess: function(data, row) {
            updateTooltips();
            this.changeStatus(row, statusType.FETCH_SUCCESS);
            this.showButtons(row);
            // Sort loaded data according to current order
            var sortColumns = this.grid.getSortColumns();
            if (sortColumns.length) {
                var sortColumn = sortColumns[0];
                row._node.sort(sortColumn.columnId, sortColumn.sortAsc);
            } else {
                row.sort(Rubeus.Sort.defaultColumn, Rubeus.Sort.defaultAsc);
            }
            this.tree.updateDataView(true);
        },
        fetchError: function(error, row) {
            this.changeStatus(row, statusType.FETCH_ERROR);
        },
        fetchStart: function(row) {
            this.changeStatus(row, statusType.FETCH_START);
        },
        uploadProgress: function(file, progress, bytesSent, row) {
            if (progress === 100) {
                var sendingTo = row.addonFullname || 'external service...';
                this.changeStatus(row, ['Sending to ', sendingTo, '. Please wait...'].join(''));
            } else{
                this.changeStatus(row, statusType.UPLOAD_PROGRESS, progress);
            }
        },
        downloadUrl: function(row) {
            return row.urls.download;
        },
        deleteUrl: function(row) {
            // Must use square bracket notation since 'delete' is a reserved word
            return row.urls['delete'];
        },
        onClickDelete: function(evt, row) {
            var self = this;
            var $elem = $(evt.target);
            bootbox.confirm({
                message: '<strong>NOTE</strong>: This action is irreversible.',
                title: 'Delete <em class="overflow">' + row.name + '</em>?',
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

        uploadAdded: function(file, row, folder) {
            // Attach upload parameters to file object for use in `uploadFiles`
            file.method = resolveCfgOption.call(this, folder, 'uploadMethod', [folder]) || 'POST';
            file.url = folder.urls.upload || resolveCfgOption.call(this, folder, 'uploadUrl', [folder]);
            // Need to set the added row's addon for other callbacks to work
            var parent = this.getByID(row.parentID);
            row.addon = parent.addon;
            // expand the folder
            this.expandItem(folder);
            var cfgOption = resolveCfgOption.call(this, row, 'uploadAdded', [file, row]);
            return cfgOption || null;
        },
        uploadSending: function(file, row, xhr, formData) {
            var cfgOption = resolveCfgOption.call(this, row, 'uploadSending', [file, row, xhr, formData]);
            return cfgOption || null;
        },
        uploadError: function(file, message, item, folder) {
            var messageText = resolveCfgOption.call(this, folder, 'uploadError', [file, message, item, folder]);
            if (!messageText) {
                if (typeof(message) === 'string') {
                    messageText = message;
                } else {
                    messageText = message.message_long;
                }
            }
            // FIXME: can't use change status, because the folder item is updated
            // on complete, which replaces the html row element
            // for now, use GrowlBox
            $.osf.growl('Upload Error:', messageText);
        },
        uploadSuccess: function(file, row, data) {
            // If file hasn't changed, remove the duplicate item
            // TODO: shows status in parent for now because the duplicate item
            // is removed and we don't have access to the original row for the file
            var self = this;
            if (data.actionTaken === null) {
                self.changeStatus(row, statusType.NO_CHANGES);
                self.delayRemoveRow(row);
            } else if (data.actionTaken === 'file_updated') {
                self.changeStatus(row, statusType.UPDATED);
                self.delayRemoveRow(row);
            } else{
                // Update the row with the returned server data
                // This is necessary for the download and delete button to work.
                $.extend(row, data);
                this.updateItem(row);
                this.changeStatus(row, statusType.UPLOAD_SUCCESS, null, 2000,
                    function(row) {
                        self.showButtons(row);
                    });
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
                selector: '.' + HGrid.Html.itemNameClass,
                callback: onClickName
            },
            // Toggle folder collapse when text is clicked; listen on text
            // rather than name to avoid Chrome crash on <select>s
            {
                on: 'click',
                selector: '.' + Rubeus.Html.folderTextClass,
                callback: onClickFolderName
            }
        ],
        progBar: '#filebrowserProgressBar',
        init: function() {
            var self = this;
            // Expand all first level items
            self.getData().forEach(function(item) {
                self.expandItem(item);
            });
            // Set default sort order
            self.grid.setSortColumn(Rubeus.Sort.defaultColumn, Rubeus.Sort.defaultAsc);
            self.getData()[0]._node.sort(Rubeus.Sort.defaultColumn, Rubeus.Sort.defaultAsc);
            updateTooltips();
            $(this.options.progBar).hide();
        },
        // Add a red highlight when user drags over a folder they don't have
        // permission to upload to.
        onDragover: function(evt, row) {
            if (row && !row.permissions.view) {
                this.addHighlight(row, 'highlight-denied');
            }
        },
        onDragleave: function(evt, row) {
            this.removeHighlight('highlight-denied');
        },
        uploadDenied: function(evt, row) {
            this.removeHighlight('highlight-denied');
        }
    };

    function updateTooltips() {
        $('[data-toggle="tooltip"]').tooltip({animation: false});
    }

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

    ///////////////////
    // Icon "Plugin" //
    ///////////////////

    Rubeus.Extensions = ['3gp', '7z', 'ace', 'ai', 'aif', 'aiff', 'amr', 'asf', 'asx', 'bat', 'bin', 'bmp', 'bup',
        'cab', 'cbr', 'cda', 'cdl', 'cdr', 'chm', 'dat', 'divx', 'dll', 'dmg', 'doc', 'docx', 'dss', 'dvf', 'dwg',
        'eml', 'eps', 'exe', 'fla', 'flv', 'gif', 'gz', 'hqx', 'htm', 'html', 'ifo', 'indd', 'iso', 'jar',
        'jpeg', 'jpg', 'lnk', 'log', 'm4a', 'm4b', 'm4p', 'm4v', 'mcd', 'mdb', 'mid', 'mov', 'mp2', 'mp3', 'mp4',
        'mpeg', 'mpg', 'msi', 'mswmm', 'ogg', 'pdf', 'png', 'pps', 'ps', 'psd', 'pst', 'ptb', 'pub', 'qbb',
        'qbw', 'qxd', 'ram', 'rar', 'rm', 'rmvb', 'rtf', 'sea', 'ses', 'sit', 'sitx', 'ss', 'swf', 'tgz', 'thm',
        'tif', 'tmp', 'torrent', 'ttf', 'txt', 'vcd', 'vob', 'wav', 'wma', 'wmv', 'wps', 'xls', 'xpi', 'zip',
        'xlsx', 'py'];

    // Uses fatcow icons
    // License: Creative Commons (Attribution 3.0 United States)
    // https://creativecommons.org/licenses/by/3.0/us/
    Rubeus.ExtensionSkeleton = '<img class="hg-icon" src="/static\/img\/hgrid\/fatcowicons\/file_extension_{{ext}}.png">';

    Rubeus.getIcon = function(item) {
        var ext = item.name.split('.').pop().toLowerCase();
        return Rubeus.Extensions.indexOf(ext) === -1 ?
                    HGrid.Html.fileIcon :
                    Rubeus.ExtensionSkeleton.replace('{{ext}}', ext);
    };

    return Rubeus;
}));

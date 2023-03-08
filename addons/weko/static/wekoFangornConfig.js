'use strict';

const ko = require('knockout');
const m = require('mithril');
const $ = require('jquery');
const Raven = require('raven-js');

const fangorn = require('js/fangorn');
const Fangorn = fangorn.Fangorn;
const $osf = require('js/osfHelpers');

const _ = require('js/rdmGettext')._;
const sprintf = require('agh.sprintf').sprintf;

const logPrefix = '[weko]';
const refreshingIds = {};
const metadataRefreshingRetries = 3;
const metadataRefreshingTimeout = 1000;
const metadataRefreshingTimeoutExp = 2;
var fileViewButtons = null;
var hashProcessed = false;
var uploadCount = 0;
var uploadReservedHandler = null;

// Define Fangorn Button Actions
const wekoItemButtons = {
    view: function (ctrl, args, children) {
        const buttons = [];
        const tb = args.treebeard;
        const item = args.item;
        const mode = tb.toolbarMode;

        if (tb.options.placement !== 'fileview') {
            if ((item.data.extra || {}).weko === 'item') {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function(event) {
                            gotoItem(item);
                        },
                        icon: 'fa fa-external-link',
                        className : 'text-info'
                    }, _('View')));
                const aritem = Object.assign({}, item);
                aritem.data = Object.assign({}, item.data, {
                    permissions: {
                        view: true,
                        edit: false
                    }
                });
                buttons.push(
                    m.component(Fangorn.Components.defaultItemButtons,
                        {treebeard : tb, mode : mode, item : aritem })
                );
            } else if ((item.data.extra || {}).weko === 'index') {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function(event) {
                            gotoItem(item);
                        },
                        icon: 'fa fa-external-link',
                        className : 'text-info'
                    }, _('View')));
                const aritem = Object.assign({}, item);
                aritem.data = Object.assign({}, item.data, {
                    permissions: {
                        view: true,
                        edit: true
                    }
                });
                buttons.push(
                    m.component(Fangorn.Components.defaultItemButtons,
                        {treebeard : tb, mode : mode, item : aritem })
                );
            } else if ((item.data.extra || {}).weko === 'draft') {
                const metadata = contextVars.metadata && contextVars.metadata.getFileMetadata(
                    item.data.nodeId,
                    item.data.provider + item.data.materialized
                );
                if (metadata) {
                    buttons.push(m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            deposit(tb, item);
                        },
                        icon: 'fa fa-upload',
                        className: 'text-success weko-button-publish'
                    }, _('Deposit')));
                }
                buttons.push(m.component(Fangorn.Components.defaultItemButtons, {
                    treebeard : tb, mode : mode, item : item
                }));
            } else if ((item.data.extra || {}).weko === 'file') {
                const aritem = Object.assign({}, item);
                aritem.data = Object.assign({}, item.data, {
                    permissions: {
                        view: true,
                        edit: false
                    }
                });
                return m.component(Fangorn.Components.defaultItemButtons,
                    {treebeard : tb, mode : mode, item : aritem });
            } else if ((item.data.extra || {}).weko) {
                console.warn('Unknown weko metadata type: ', (item.data.extra || {}).weko);
            } else if (item.data.kind === 'folder' && item.data.addonFullname) {
                const aritem = Object.assign({}, item);
                aritem.data = Object.assign({}, item.data, {
                    permissions: {
                        view: true,
                        edit: true
                    }
                });
                return m.component(Fangorn.Components.defaultItemButtons,
                    {treebeard : tb, mode : mode, item : aritem });
            } else {
                return m.component(Fangorn.Components.defaultItemButtons,
                                      {treebeard : tb, mode : mode, item : item });
            }
        }
        return m('span', buttons);
    }
};

function gotoItem (item) {
    if (item.data && item.data.extra && item.data.extra.weko === 'draft') {
        const url = fangorn.getPersistentLinkFor(item);
        window.location.href = url;
        return;
    }
    if (!(item.data.extra || {}).weko_web_url) {
        throw new Error('Missing properties');
    }
    window.open(item.data.extra.weko_web_url, '_blank');
}

function wekoFolderIcons(item) {
    if (item.data.iconUrl) {
        return m('img', {
            src: item.data.iconUrl,
            style: {
                width: '16px',
                height: 'auto'
            }
        }, ' ');
    }
    return undefined;
}

function wekoWEKOTitle(item, col) {
    var tb = this;
    if (item.data.isAddonRoot && item.connected === false) {
        return Fangorn.Utils.connectCheckTemplate.call(this, item);
    }
    if (item.data.unavailable && (item.data.name || '').match(/is not configured$/)) {
        return Fangorn.Utils.connectCheckTemplate.call(this, item);
    }
    if (item.data.addonFullname) {
        return m('span', [m('span', item.data.name)]);
    } else {
        const contents = [
            m('span.fg-file-links',
                {
                    onclick: function () {
                        gotoItem(item);
                    }
                },
                item.data.name
            )
        ];
        if ((item.data.extra || {}).weko === 'draft') {
            contents.push(
                m('span.text.text-muted', ' [Draft]')
            );
        }
        return m('span', contents);
    }
}

function wekoColumns(item) {
    const treebeard = this;
    checkAndReserveRefreshingMetadata(
        item,
        function(item) {
            const parentItem = findItem(treebeard.treeData, item.parentID);
            reserveDeposit(treebeard, item, function() {
                treebeard.updateFolder(null, parentItem);
            });
        }
    );
    var tb = this;
    var columns = [];
    columns.push({
        data : 'name',
        folderIcons : true,
        filter : true,
        custom: wekoWEKOTitle
    });
    item.css = (item.css || '') + ' weko-row';
    return columns;
}

function findItem(item, item_id) {
    if(item.id == item_id) {
        return item;
    }else if(item.children){
        for(var i = 0; i < item.children.length; i ++) {
            const found = findItem(item.children[i], item_id);
            if(found) {
                return found;
            }
        }
    }
    return null;
}

function showError(tb, message) {
    if (!tb) {
        $osf.growl('WEKO Error:', message);
        return;
    }
    var modalContent = [
            m('p.m-md', message)
        ];
    var modalActions = [
            m('button.btn.btn-primary', {
                    'onclick': function () {
                        tb.modal.dismiss();
                    }
                }, 'Okay')
        ];
    tb.modal.update(modalContent, modalActions, m('h3.break-word.modal-title', 'Error'));
}

function performDeposit(tb, contextItem, options) {
    console.log(logPrefix, 'publish', contextItem, options);
    const extra = contextItem.data.extra;
    var url = contextVars.node.urls.api;
    if (!url.match(/.*\/$/)) {
        url += '/';
    }
    url += 'weko/index/' + extra.index
        + '/files/' + contextItem.data.nodeId + '/' + contextItem.data.provider
        + contextItem.data.materialized;
    startDepositing(tb, contextItem);
    const params = {};
    if (options.schema) {
        params.schema_id = options.schema;
    }
    if (options.project_metadatas) {
        params.project_metadata_ids = options.project_metadatas.join(',');
    }
    return $osf.putJSON(url, params).done(function (data) {
      console.log(logPrefix, 'checking progress...');
      checkDepositing(tb, contextItem, url);
    }).fail(function(xhr, status, error) {
      cancelDepositing(tb, contextItem);
      const message = _('Error occurred: ') + error;
      showError(tb, message);
      Raven.captureMessage('Error while depositing file', {
        extra: {
            url: url,
            status: status,
            error: error
        }
      });
    });
}

function checkDepositing(tb, contextItem, url) {
    return $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json'
    }).done(function (data) {
        console.log(logPrefix, 'loaded: ', data);
        if (data.data && data.data.attributes && data.data.attributes.error) {
            cancelDepositing(tb, contextItem);
            const message = _('Error occurred: ') + data.data.attributes.error;
            showError(tb, message);
            return;
        }
        if (data.data && data.data.attributes && data.data.attributes.result) {
            console.log(logPrefix, 'uploaded', data.data.attributes.result);
            if (tb) {
                tb.updateFolder(null, findItem(tb.treeData, contextItem.parentID));
            } else {
                $('#weko-deposit i')
                    .addClass('fa-upload')
                    .removeClass('fa-spinner fa-pulse');
                $('#weko-deposit').removeClass('disabled');
                $osf.growl('Success', _('Deposit was successful.'), 'success');
                const baseUrl = contextVars.node.urls.web + 'files/dir/' + contextItem.data.provider;
                const index = contextItem.data.materialized.lastIndexOf('/');
                window.location.href = baseUrl + contextItem.data.materialized.substring(0, index + 1);
            }
            return;
        }
        if (data.data && data.data.attributes && data.data.attributes.progress) {
            contextItem.data.progress = data.data.attributes.progress.rate || 0;
            contextItem.data.uploadState = function() {
                return 'uploading';
            };
            if (tb) {
                tb.redraw();
            }
        }
        setTimeout(function() {
            checkDepositing(tb, contextItem, url);
        }, 1000);
    }).fail(function(xhr, status, error) {
        if (status === 'error' && error === 'NOT FOUND') {
            setTimeout(function() {
                checkDepositing(tb, contextItem, url);
            }, 1000);
            return;
        }
        cancelDepositing(tb, contextItem);
        const message = _('Error occurred: ') + error;
        showError(tb, message);
        Raven.captureMessage('Error while retrieving addon info', {
            extra: {
                url: url,
                status: status,
                error: error
            }
        });
    });
}

function startDepositing(tb, item) {
    if (!tb) {
        $('#weko-deposit i')
            .removeClass('fa-upload')
            .addClass('fa-spinner fa-pulse');
        $('#weko-deposit').addClass('disabled');
        return;
    }
    item.inProgress = true;
    item.data.progress = 0;
    item.data.uploadState = function() {
        return 'pending';
    };
    tb.redraw();
}

function cancelDepositing(tb, item) {
    if (!tb) {
        $('#weko-deposit i')
            .addClass('fa-upload')
            .removeClass('fa-spinner fa-pulse');
        $('#weko-deposit').removeClass('disabled');
        return;
    }
    item.inProgress = false;
    item.data.progress = 100;
    item.data.uploadState = null;
    tb.redraw();
}

function reserveDeposit(treebeard, item, cancelCallback) {
    if (uploadCount <= 0) {
        deposit(treebeard, item, cancelCallback);
        return;
    }
    if (uploadReservedHandler) {
        console.warn(logPrefix, 'Upload handler already reserved', item);
        return;
    }
    console.log(logPrefix, 'Reserve upload handler', item);
    uploadReservedHandler = function() {
        deposit(treebeard, item, cancelCallback);
    };
}

function deposit(treebeard, item, cancelCallback) {
    showConfirmDeposit(treebeard, item, function(deposit, options) {
        if (!deposit) {
            if (!cancelCallback) {
                return;
            }
            cancelCallback();
            return;
        }
        performDeposit(treebeard, item, options || {});
    });
}

function createMetadataSelectorBase(item, schemaCallback, projectMetadataCallback, errorCallback) {
    if (!contextVars.metadata) {
        throw new Error('Metadata addon is not available');
    }
    const fileMetadata = contextVars.metadata.getFileMetadata(
        item.data.nodeId,
        item.data.provider + item.data.materialized
    );
    if (!fileMetadata) {
        throw new Error('File metadata is not found');
    }
    const targetIndex = item.data.extra && item.data.extra.index;
    if (!targetIndex) {
        throw new Error('Extra field is not found');
    }
    var registrations = {};
    function loadHandler() {
        contextVars.metadata.getRegistrations(function(error, r) {
            if (error) {
                console.error(logPrefix, 'Error while retrieving registrations', error);
                if (errorCallback) {
                    errorCallback('retrieving registrations', error);
                }
                return;
            }
            registrations['registrations'] = r.registrations;
            if (projectMetadataCallback) {
                projectMetadataCallback(registrations);
            }
        });
        contextVars.metadata.getDraftRegistrations(function(error, r) {
            if (error) {
                console.error(logPrefix, 'Error while retrieving draft registrations', error);
                if (errorCallback) {
                    errorCallback('retrieving draft registrations', error);
                }
                return;
            }
            registrations['draftRegistrations'] = r.registrations;
            if (projectMetadataCallback) {
                projectMetadataCallback(registrations);
            }
        });
    }
    loadHandler();
    if (schemaCallback) {
        const url = item.data.nodeApiUrl + 'weko/schemas/';
        console.log(logPrefix, 'loading: ', url);
        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function (data) {
            const schemas = (data.data.attributes || [])
                .filter(function(r) {
                    const items = fileMetadata.items || [];
                    return items.find(function(i) {
                        return i.schema === r.id;
                    });
                });
            schemaCallback(schemas);
        })
        .fail(function(xhr, status, error) {
            Raven.captureMessage('Error while retrieving addon info', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
            if (errorCallback) {
                errorCallback('retrieving addon info', error);
            }
        });
    }
    return {
        fileMetadata: fileMetadata,
        refreshHandler: loadHandler
    };
}

function createMetadataSelectorForJQuery(item, changedCallback) {
    const errorView = $('<div></div>').addClass('alert alert-danger').hide();
    const metadataSelect = $('<div></div>').hide();
    const schemaLoading = $('<span></span>').addClass('fa fa-spinner fa-pulse').show();
    const metadataLoading = $('<span></span>').addClass('fa fa-spinner fa-pulse').show();
    const refreshButton = $('<button></button>')
        .addClass('btn btn-sm')
        .append($('<span></span>').addClass('fa fa-refresh'))
        .attr('disabled', 'disabled');
    const schemaSelect = $('<select></select>').addClass('form-control');
    var lastSchema = null;
    var lastSchemaValid = null;
    function getMetadataSelectValue() {
        return metadataSelect.find('input:checked').map(function() {
            return $(this).val();
        }).get();
    }
    function valueChanged() {
        var valid = false;
        if (lastSchemaValid === null || lastSchema !== schemaSelect.val()) {
            valid = validateSchema(schemaSelect.val());
        } else {
            valid = lastSchemaValid;
        }
        if (!changedCallback) {
            return;
        }
        changedCallback(valid, schemaSelect.val(), getMetadataSelectValue());
    }
    var selector = null;
    function validateSchema(schema) {
        if (!schema) {
            return false;
        }
        const items = selector.fileMetadata.items.filter(function(i) {
            return i.schema === schema;
        });
        if (items.length === 0) {
            throw new Error('Schema not found');
        }
        return true;
    }
    var registrationsCache = null;
    const projectMetadataCallback = function(registrations) {
        if (!registrations.registrations || !registrations.draftRegistrations) {
            return;
        }
        registrationsCache = registrations;
        metadataSelect.empty().show();
        metadataLoading.hide();
        refreshButton.attr('disabled', null);
        (registrations.registrations || []).forEach(function(r) {
            if (!(r.relationships && r.relationships.registration_schema && r.relationships.registration_schema.data &&
                r.relationships.registration_schema.data.id === schemaSelect.val())) {
                return;
            }
            const title = r.attributes.title || contextVars.metadata.extractProjectName(r.attributes.registered_meta);
            const registered = new Date(Date.parse(r.attributes.date_registered));
            metadataSelect.append($('<div></div>')
                .append($('<input></input>')
                    .attr('type', 'checkbox')
                    .attr('value', 'registration/' + r.id)
                    .change(valueChanged))
                .append($('<span></span>')
                    .text(title + ' (' + registered + ')')));
        });
        (registrations.draftRegistrations || []).forEach(function(r) {
            if (!(r.relationships && r.relationships.registration_schema && r.relationships.registration_schema.data &&
                r.relationships.registration_schema.data.id === schemaSelect.val())) {
                return;
            }
            const title = r.attributes.title || contextVars.metadata.extractProjectName(r.attributes.registration_metadata);
            const updated = new Date(Date.parse(r.attributes.datetime_updated));
            metadataSelect.append($('<div></div>')
                .append($('<input></input>')
                    .attr('type', 'checkbox')
                    .attr('value', 'draft-registration/' + r.id)
                    .change(valueChanged))
                .append($('<span></span>')
                    .text(title + ' (' + updated + ')')));
        });
    };
    const errorCallback = function(action, error) {
        errorView.text(_('Error occurred while ') + action + ': ' + error).show();
    };
    const schemaCallback = function(schemas) {
        (schemas || []).forEach(function(s) {
            schemaSelect.append($('<option></option>').attr('value', s.id).text(s.attributes.name));
        });
        schemaLoading.hide();
        valueChanged();
    };
    selector = createMetadataSelectorBase(item, schemaCallback, projectMetadataCallback, errorCallback);
    metadataSelect.change(valueChanged);
    schemaSelect.change(function() {
        if (registrationsCache) {
            projectMetadataCallback(registrationsCache);
        }
        valueChanged();
    });
    refreshButton.click(function() {
        metadataLoading.show();
        errorView.hide();
        selector.refreshHandler();
        refreshButton.attr('disabled', 'disabled');
    });
    const schemaSelectPanel = $('<div></div>').addClass('form-group')
        .append($('<label></label>').text(_('Schema')))
        .append(schemaLoading)
        .append(schemaSelect)
        .append($('<div></div>').addClass('help-block').text(_('Select a schema for the file.')));
    const metadataSelectPanel = $('<div></div>').addClass('form-group')
        .append($('<label></label>').text(_('Project Metadata')))
        .append(metadataLoading)
        .append(refreshButton)
        .append(metadataSelect)
        .append($('<div></div>').addClass('help-block').text(_('Select a registration for the file.')));
    return $('<div></div>')
        .append(errorView)
        .append(schemaSelectPanel)
        .append(metadataSelectPanel);
}

function showConfirmDeposit(tb, contextItem, callback) {
    var options = {};
    const okHandler = function (dismiss) {
        dismiss()
        if (!callback) {
            return;
        }
        callback(true, options);
    };
    const cancelHandler = function (dismiss) {
        dismiss()
        if (!callback) {
            return;
        }
        callback(false);
    };
    const message = sprintf(
        _('Do you want to deposit the file/folder "%1$s" to WEKO? This operation is irreversible.'),
        $osf.htmlEscape(contextItem.data.name)
    );
    const dialog = $('<div class="modal fade" data-backdrop="static"></div>');
    const close = $('<a href="#" class="btn btn-default" data-dismiss="modal"></a>').text(_('Cancel'));
    close.click(function() {
        cancelHandler(function() {
            dialog.modal('hide');
        });
    });
    const save = $('<a href="#" class="btn btn-primary"></a>').text(_('OK'));
    save.click(function() {
        okHandler(function() {
            dialog.modal('hide');
        });
    });
    const optionsHandler = function(valid, schema, projectMetadatas) {
        options.schema = schema;
        options.project_metadatas = projectMetadatas;
    };
    dialog
        .append($('<div class="modal-dialog modal-lg"></div>')
            .append($('<div class="modal-content"></div>')
                .append($('<div class="modal-header"></div>')
                    .append($('<h3></h3>').text(_('Deposit files'))))
                .append($('<div class="modal-body"></div>')
                    .append($('<p></p>').append(message))
                    .append(createMetadataSelectorForJQuery(contextItem, optionsHandler))
                .append($('<div class="modal-footer"></div>')
                    .css('display', 'flex')
                    .css('align-items', 'center')
                    .append(close.css('margin-left', 'auto'))
                    .append(save)))));
    dialog.appendTo($('#treeGrid'));
    dialog.modal('show');
}

function checkAndReserveRefreshingMetadata(item, callback) {
    if (!item.data) {
        return;
    }
    const id = item.data.id;
    if (refreshingIds[id]) {
        // Already reserved
        return;
    }
    const metadatas = searchMetadatas(item);
    if (metadatas.length === 0 || metadatas.some(function(m) {
        return m.metadata === undefined;
    })) {
        // Not loaded
        return;
    }
    if (metadatas.every(function(m) {
        return m.metadata;
    })) {
        // Already loaded
        return;
    }
    refreshingIds[id] = Date.now();
    reserveMetadataRefresh(
        item,
        metadataRefreshingTimeout,
        metadataRefreshingRetries,
        callback
    );
}

function reserveMetadataRefresh(item, timeout, retries, callback) {
    if (!contextVars.metadata) {
        console.warn('Metadata addon is not available');
        return;
    }
    console.log(logPrefix, 'reserveRefreshMetadata', item);
    setTimeout(function() {
        contextVars.metadata.loadMetadata(
            item.data.nodeId,
            item.data.nodeApiUrl,
            function() {
                const metadatas = searchMetadatas(item);
                if (metadatas.length > 0 && metadatas.every(function(m) {
                    return m.metadata;
                })) {
                    console.log(logPrefix, 'metadata refreshed', metadatas, item);
                    refreshingIds[item.data.id] = null;
                    if (!callback) {
                        return;
                    }
                    callback(item);
                    return;
                }
                console.log(logPrefix, 'refreshMetadata', metadatas, item);
                if (retries <= 0) {
                    console.log(logPrefix, 'Metadata refreshing cancelled', item);
                    return;
                }
                reserveMetadataRefresh(
                    item,
                    timeout * metadataRefreshingTimeoutExp,
                    retries - 1,
                    callback
                );
            }
        );
    }, timeout);
}

function searchMetadatas(tree, recursive) {
    const data = tree.data;
    var r = [];
    if (data.extra && data.extra.weko === 'draft' && isTopLevelDraft(tree)) {
        if (!contextVars.metadata) {
            return [];
        }
        const metadata = contextVars.metadata.getFileMetadata(
            data.nodeId,
            data.provider + data.materialized
        );
        r.push({
            metadata: metadata,
            item: tree
        });
    } else if (recursive && ((data.extra && data.extra.weko === 'index') || data.addonFullname === 'WEKO')) {
        (tree.children || []).forEach(function(item) {
            r = r.concat(searchMetadatas(item, recursive));
        });
    }
    return r;
}

function isTopLevelDraft(item) {
    const data = item.data;
    if (!data) {
        return false;
    }
    const extra = data.extra;
    if (!extra) {
        return false;
    }
    const source = extra.source;
    if (!source) {
        return false;
    }
    const path = source.materialized_path;
    if (!path) {
        return false;
    }
    return path.match(/^\/\.weko\/[^\/]+\/[^\/]+\/?$/);
}

function refreshFileViewButtons(item) {
    if (item.data.provider !== 'weko') {
        return;
    }
    if (!isTopLevelDraft(item)) {
        return;
    }
    const metadata = contextVars.metadata && contextVars.metadata.getFileMetadata(
        item.data.nodeId,
        item.data.provider + item.data.materialized
    );
    if (!metadata) {
        console.warn(logPrefix, 'Metadata not found', item);
        return;
    }
    if (!fileViewButtons) {
        fileViewButtons = $('<div></div>')
            .addClass('btn-group m-t-xs')
            .attr('id', 'weko-toolbar');
    }
    const buttons = fileViewButtons;
    buttons.empty();
    const btn = $('<button></button>')
        .addClass('btn')
        .addClass('btn-sm')
        .addClass('btn-success')
        .attr('id', 'weko-deposit');
    btn.append($('<i></i>').addClass('fa fa-upload'));
    btn.click(function(event) {
        deposit(null, item);
    });
    btn.append($('<span></span>').text(_('Deposit')));
    buttons.append(btn);
    $('#toggleBar .btn-toolbar').append(fileViewButtons);
}

function processHash(item) {
    if (hashProcessed) {
        return;
    }
    if (window.location.hash !== '#deposit') {
        return;
    }
    if (item.data.provider !== 'weko') {
        return;
    }
    hashProcessed = true;
    deposit(null, item);
}

function initFileView() {
    const observer = new MutationObserver(refreshIfToolbarExists);
    function refreshIfToolbarExists() {
        const toolbar = $('#toggleBar .btn-toolbar');
        if (toolbar.length === 0) {
            return;
        }
        const item = {
            data: Object.assign(
                {},
                contextVars.file,
                {
                    nodeId: contextVars.node.id,
                    nodeApiUrl: contextVars.node.urls.api,
                    materialized: contextVars.file.materialized || contextVars.file.materializedPath
                }
            )
        };
        function refreshIfMetadataNotLoaded() {
            console.log(logPrefix, 'Checking metadata...', contextVars.metadataAddonEnabled, contextVars.metadata);
            if (contextVars.metadataAddonEnabled && (!contextVars.metadata ||
                !contextVars.metadata.getProjectMetadata(item.data.nodeId) ||
                contextVars.metadata.getProjectMetadata(item.data.nodeId).files === undefined)) {
                setTimeout(refreshIfMetadataNotLoaded, 500);
                return;
            }
            refreshFileViewButtons(item);
            setTimeout(function() {
                processHash(item);
            }, 0);
        }
        setTimeout(refreshIfMetadataNotLoaded, 500);
    }
    const toggleBar = $('#toggleBar').get(0);
    observer.observe(toggleBar, {attributes: false, childList: true, subtree: false});
}

function wekoUploadAdd(file, item) {
    console.log(logPrefix, 'Detected: uploadAdded', file);
    uploadCount ++;
}

function wekoUploadSuccess(file, row) {
    console.log(logPrefix, 'Detected: uploadSuccess', file);
    uploadCount --;
    if (!uploadReservedHandler) {
        return;
    }
    if (uploadCount > 0) {
        console.log(logPrefix, 'Reserved upload handler exists. waiting for ', uploadCount, ' files');
        return;
    }
    console.log(logPrefix, 'Processing reserved upload handler...');
    const f = uploadReservedHandler;
    uploadReservedHandler = null;
    setTimeout(function() {
        // If uploadAdded is called immediately afterwards, then revert to the reserved state again.
        if (uploadCount > 0) {
            console.log(logPrefix, 'Reserved upload handler restored');
            uploadReservedHandler = f;
            return;
        }
        f();
        console.log(logPrefix, 'Reserved upload handler processed');
    }, 500);
}

function addDepositButtonToMetadataDialog() {
    var metadataHandlers = contextVars.metadataHandlers;
    if (!metadataHandlers) {
        contextVars.metadataHandlers = metadataHandlers = {};
    }
    metadataHandlers.weko = {
        text: _('Save and Deposit to WEKO'),
        click: function(item, schema, fileMetadata) {
            if (!item.data.nodeApiUrl) {
                const item_ = {
                    data: Object.assign({
                        nodeApiUrl: contextVars.node.urls.api
                    }, item.data),
                }
                deposit(null, item_);
                return;
            }
            deposit(null, item);
        }
    };
}

Fangorn.config.weko = {
    folderIcon: wekoFolderIcons,
    itemButtons: wekoItemButtons,
    resolveRows: wekoColumns,
    uploadAdd: wekoUploadAdd,
    uploadSuccess: wekoUploadSuccess,
};

addDepositButtonToMetadataDialog();

if ($('#fileViewPanelLeft').length > 0) {
    // File View
    initFileView();
}
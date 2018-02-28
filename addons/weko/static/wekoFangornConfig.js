'use strict';

var ko = require('knockout');
var m = require('mithril');
var URI = require('URIjs');
var $ = require('jquery');
var Raven = require('raven-js');

var Fangorn = require('js/fangorn').Fangorn;
var waterbutler = require('js/waterbutler');
var $osf = require('js/osfHelpers');

function changeState(grid, item, version) {
    item.data.version = version;
    grid.updateFolder(null, item);
}

function getLastPathComponent(itemData) {
    if(itemData.path === undefined) {
        return undefined;
    }
    var pathcomps = itemData.path.split('/');
    if(itemData.kind == 'folder') {
        return pathcomps[pathcomps.length - 2];
    } else {
        return pathcomps[pathcomps.length - 1];
    }
}

// Define Fangorn Button Actions
var _wekoItemButtons = {
    view: function (ctrl, args, children) {
        var buttons = [];
        var tb = args.treebeard;
        var item = args.item;
        var mode = tb.toolbarMode;

        function _uploadEvent(event, item, col) {
            event.stopPropagation();
            tb.dropzone.hiddenFileInput.click();
            tb.dropzoneItemCache = item;
        }

        function startCreatingIndex(event, item, col) {
            console.log('Show modal dialog...');
            console.log(item);
            var indexDesc = { 'title_ja': m.prop(''),
                              'title_en': m.prop('') };
            var modalContent = [m('.form-group', [
                                    m('label', 'Title(ja)'),
                                    m('input[type="text"].form-control', {
                                            'onchange': m.withAttr('value', indexDesc.title_ja),
                                            'placeholder': 'New index name(ja)'
                                        })
                                  ]),
                                m('.form-group', [
                                    m('label', 'Title(en)'),
                                    m('input[type="text"].form-control', {
                                            'onchange': m.withAttr('value', indexDesc.title_en),
                                            'placeholder': 'New index name(en)'
                                        })
                                  ])];
            var modalActions = [m('button.btn.btn-default', {
                    'onclick': function () {
                        tb.modal.dismiss();
                    }
                }, 'Cancel'),
                m('button.btn.btn-primary', {
                    'onclick': function () {
                        createIndex(item,
                                    indexDesc.title_ja(),
                                    indexDesc.title_en(),
                                    function() { tb.modal.dismiss(); });
                    }
                }, 'Next')];
            tb.modal.update(modalContent, modalActions,
                            m('h3.break-word.modal-title', 'Input descriptions about new index'));
        }

        function createIndex(parentItem, titleJa, titleEn, dismissCallback) {
            console.log('Creating... ' + item + ' - ' + titleJa + ' - ' + titleEn);
            var parentIndex = null;
            if(parentItem.data.extra) {
                parentIndex = parentItem.data.extra.indexId;
            }
            $osf.postJSON(
                    item.data.nodeApiUrl + 'weko/indices/',
                    ko.toJS({
                        parent_index: parentIndex,
                        title_ja: titleJa,
                        title_en: titleEn
                    })
                ).done(function(item){
                    console.log('Created', item);
                    item = tb.createItem(item, parentItem.id);
                    item.notify.update('New index created!', 'success',
                                       undefined, 1000);
                    if(dismissCallback) {
                        dismissCallback();
                    }
                });
        }

        if (tb.options.placement !== 'fileview') {
            var lastItem = getLastPathComponent(item.data);
            if(item.data.addonFullname || (lastItem != null && lastItem.startsWith('weko:'))) {
                if (item.kind === 'folder') {
                    buttons.push(m.component(Fangorn.Components.button, {
                                                 onclick: function(event) {
                                                     startCreatingIndex.call(tb, event, item);
                                                 },
                                                 icon: 'fa fa-plus',
                                                 className: 'text-success'
                                             }, 'Create Index'));
                    buttons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                _uploadEvent.call(tb, event, item);
                            },
                            icon: 'fa fa-upload',
                            className: 'text-success'
                        }, 'Upload')
                    );
                    buttons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function () {
                                mode(Fangorn.Components.toolbarModes.ADDFOLDER);
                            },
                            icon: 'fa fa-plus',
                            className: 'text-success'
                        }, 'Create Folder')
                    );
                } else if (item.kind === 'file') {
                    buttons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                Fangorn.ButtonEvents._removeEvent.call(tb, event, [item]);
                            },
                            icon: 'fa fa-trash',
                            className: 'text-danger'
                        }, 'Delete')
                    );
                    buttons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function(event) {
                                gotoItem(item);
                            },
                            icon: 'fa fa-external-link',
                            className : 'text-info'
                        }, 'View'));
                }
            }else{
                if(item.data.extra != null && item.data.extra.archivable) {
                    buttons.push(m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            _publish(tb, _findItem(tb.treeData, item.parentID),
                                     item, item.data);
                        },
                        icon: 'fa fa-upload',
                        className: 'text-primary weko-button-publish'
                    }, 'Publish'));
                }
                var defaultButtons = m.component(Fangorn.Components.defaultItemButtons,
                                      {treebeard : tb, mode : mode, item : item });
                if(buttons.length == 0) {
                    return defaultButtons;
                }else{
                    return m('span', [buttons, defaultButtons]);
                }
            }
        }
        return m('span', buttons);
    }
};

function gotoItem (item) {
    var itemId = /\/weko:item([0-9]+)$/.exec(item.data.path)[1];

    $.getJSON(item.data.nodeApiUrl + 'weko/item_view/' + itemId + '/').done(function (data) {
        window.open(data.url, '_blank');
    });
}

function _fangornFolderIcons(item) {
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

function _fangornWEKOTitle(item, col) {
    var tb = this;
    if (item.data.isAddonRoot && item.connected === false) {
        return Fangorn.Utils.connectCheckTemplate.call(this, item);
    }
    if (item.data.addonFullname) {
        var contents = [m('weko-name', item.data.name)];
        return m('span', contents);
    } else {
        var contents = [m('weko-name.fg-file-links', {
                                onclick: function () {
                                    gotoFile(item);
                                }
                            }, item.data.name)]
        var lastComponent = getLastPathComponent(item.data);
        if(lastComponent !== undefined && ! lastComponent.startsWith('weko:')) {
            contents.push(
                m('span.text.text-muted', ' [Draft]')
            );
        }
        return m('span', contents);
    }
}

function _fangornColumns(item) {
    var tb = this;
    var columns = [];
    columns.push({
        data : 'name',
        folderIcons : true,
        filter : true,
        custom: _fangornWEKOTitle
    });
    return columns;
}

function _getWaterbutlerUrl() {
    var url = contextVars.waterbutlerURL;
    if(! url.endsWith('/')) {
        url += '/';
    }
    url += 'v1/resources/' + contextVars.node.id + '/providers/weko';
    return url;
}

function _getWaterbutlerParentUrl(parentItem) {
    if(parentItem.data.materialized !== undefined) {
        return _getWaterbutlerUrl() + parentItem.data.materialized;
    }else{
        return _getWaterbutlerUrl() + '/';
    }
}

function _submitDraft(tb, parentItem, contextItem, draftFileData, metadata, dismissCallback) {
    if(metadata.asWEKOExport) {
        _submitDraftZip(tb, parentItem, contextItem, draftFileData, metadata, dismissCallback);
    }else{
        _submitDraftXml(tb, parentItem, contextItem, draftFileData, metadata, dismissCallback);
    }
}

function _putMetadata(tb, parentItem, contextItem, draftFilename,
                      importFilename, importContent, dismissCallback) {
    $.ajax({
        type: 'GET',
        url: _getWaterbutlerParentUrl(parentItem),
        dataType: 'json',
        xhrFields:{withCredentials: true},
        success: function(data) {
            console.log(data);
            var jsonFiles = data.data.filter(function(d) {
                if(d.attributes && d.type == 'files') {
                    if(d.attributes.name == importFilename) {
                        return true;
                    }
                }
                return false;
              });
            var putUrl = null;
            var links = parentItem.data.links;
            var qsep = '&';
            if(links === undefined) {
                links = {'upload': _getWaterbutlerUrl() + '/'};
                qsep = '?';
            }
            if(jsonFiles.length == 0) {
                // Create file
                putUrl = links.upload + qsep + 'name=' + encodeURI(importFilename);
            }else{
                // Update file
                var baseUrl = links.upload;
                baseUrl = baseUrl.substring(0, baseUrl.lastIndexOf('/') + 1);
                putUrl =  baseUrl + encodeURI(importFilename);
            }
            console.log('Updating/Creating... ', putUrl);
            $.ajax({
                type: 'PUT',
                url: putUrl,
                dataType: 'json',
                data: importContent,
                xhrFields:{withCredentials: true},
                success: function(data) {
                    console.log(data);
                    var indexId = null;
                    if(parentItem.data.extra) {
                        indexId = parentItem.data.extra.indexId;
                    }
                    $osf.postJSON(
                            parentItem.data.nodeApiUrl + 'weko/item_log/',
                            ko.toJS({
                                index_id: indexId,
                                title: draftFilename
                            })
                        ).done(function(item){
                            console.log('Log added');
                            if(contextItem) {
                                contextItem.notify.update('Successfully published.',
                                                         'success', undefined, 1000);
                            }
                            setTimeout(dismissCallback, 1500)
                        });
                },
                error: function(xhr, textStatus, errorThrown) {
                    console.log('Error: ' + textStatus);
                    console.log(errorThrown);
                    var message = 'Error: Something went wrong when putting item. ' + textStatus;
                    _showError(tb, message);
                    dismissCallback();
                }});
        },
        error: function(xhr, textStatus, errorThrown) {
            console.log('Error: ' + textStatus, errorThrown);
            var message = 'Error: Something went wrong when retrieving item. ' + textStatus;
            _showError(tb, message);
            dismissCallback();
        }});
}

function _submitDraftXml(tb, parentItem, contextItem, draftFileData, metadata, dismissCallback) {
    console.log('confirmed', metadata, draftFileData, parentItem);
    var draftFilename = getLastPathComponent(draftFileData);
    var importXmlFilename = draftFilename + '-import.xml';
    $.get(window.contextVars.node.urls.api + 'weko/metadata/',
          ko.toJS({filename: draftFilename,
                   filenames: draftFileData.extra.content_files.join('\n'),
                   serviceItemType: metadata.serviceItemType})
        ).done(function(importXml){
            console.log('Generated', importXml);
            _putMetadata(tb, parentItem, contextItem, draftFilename,
                         importXmlFilename,
                         new XMLSerializer().serializeToString(importXml),
                         dismissCallback);
        });
}

function _submitDraftZip(tb, parentItem, contextItem, draftFileData, metadata, dismissCallback) {
    console.log('confirmed', metadata, draftFileData, parentItem);
    var draftFilename = getLastPathComponent(draftFileData);
    var importZipFilename = draftFilename + '-import.zipimport';
    _putMetadata(tb, parentItem, contextItem, draftFilename, importZipFilename,
                 '', dismissCallback);
}

function _findItem(item, item_id) {
    if(item.id == item_id) {
        return item;
    }else if(item.children){
        for(var i = 0; i < item.children.length; i ++) {
            var found = _findItem(item.children[i], item_id);
            if(found) {
                return found;
            }
        }
    }
    return null;
}

function _showError(tb, message) {
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

function _publish(tb, parentItem, contextItem, itemData) {
    $('.weko-button-publish i').attr('class', 'fa fa-spinner fa-pulse fa-3x fa-fw');
    if(itemData.extra.content_files.length == 0) {
        console.log('loading', itemData);
        $.ajax({
            type: 'GET',
            url: _getWaterbutlerParentUrl(parentItem),
            dataType: 'json',
            xhrFields:{withCredentials: true},
            success: function(data) {
                var jsonFiles = data.data.filter(function(d) {
                    if(d.attributes && d.attributes.name == itemData.name) {
                        return true;
                    }
                    return false;
                  });
                if(jsonFiles.length == 0) {
                    var message = 'Error: Something went wrong when retrieving item.';
                    _showError(tb, message);
                    $('.weko-button-publish i').attr('class', 'fa fa-upload');
                }else{
                    _processPublish(tb, parentItem, contextItem, jsonFiles[0].attributes);
                }
            },
            error: function(xhr, textStatus, errorThrown) {
                console.log('Error: ' + textStatus, errorThrown);
                var message = 'Error: Something went wrong when retrieving item. ' + textStatus;
                _showError(tb, message);
                $('.weko-button-publish i').attr('class', 'fa fa-upload');
            }});
    }else{
        _processPublish(tb, parentItem, contextItem, itemData);
    }
}

function _processPublish(tb, parentItem, contextItem, itemData) {
    console.log('publish', parentItem, itemData);
    $.getJSON(window.contextVars.node.urls.api + 'weko/serviceitemtype').done(function (data) {
        console.log('ServiceItemType loaded');
        $('.weko-button-publish i').attr('class', 'fa fa-upload');
        var fileDesc = {asWEKOExport: m.prop(false), serviceItemType: m.prop(0)};
        var modalContent = [m('.form-group', [
                               m('label', [
                                   m('input[type=checkbox]',
                                     {onchange: function() {
                                                    fileDesc.asWEKOExport(this.checked);
                                                    $('#service_item_type').prop('disabled', this.checked);
                                                },
                                      disabled: ! itemData.extra.has_import_xml}),
                                   'Import as WEKO EXPORT zip'
                                 ])
                              ]),
                            m('.form-group', [
                               m('label', 'Service item type'),
                               m('select.form-control#service_item_type',
                                  {onchange: m.withAttr('value', fileDesc.serviceItemType),
                                   disabled: fileDesc.asWEKOExport()},
                                  data.item_type.map(function(d, i){
                                      return m('option', { value: i, innerHTML: d.name });
                                  }))
                              ])];
        var modalActions = [m('button.btn.btn-default', {onclick: function () {
                                tb.modal.dismiss();
                                tb.updateFolder(null, parentItem);
                            }}, 'Cancel'),
                            m('button.btn.btn-primary', {onclick: function () {
                                $('.weko-button-publish i').attr('class', 'fa fa-spinner fa-pulse fa-3x fa-fw');
                                tb.modal.dismiss();
                                _submitDraft(tb,
                                             parentItem,
                                             contextItem,
                                             itemData,
                                             {asWEKOExport: fileDesc.asWEKOExport(),
                                              serviceItemType: fileDesc.serviceItemType()},
                                             function() {
                                                 $('.weko-button-publish i').attr('class', 'fa fa-upload');
                                                 tb.updateFolder(null, parentItem);
                                             });
                            }}, 'Submit')];
        tb.modal.update(modalContent, modalActions, m('h3.break-word.modal-title', 'Select file type'));
    }).fail(function (xhr, status, error) {
        console.log('Error: ' + status, error);
        var message = 'Error: Something went wrong when retrieving serviceitemtype. ' + status;
        _showError(tb, message);
        $('.weko-button-publish i').attr('class', 'fa fa-upload');
    });
}

function _uploadSuccess(file, item, response) {
    var tb = this;
    console.log('Uploaded', item, response);
    if(response.data.attributes.extra.archivable) {
        console.log('Publishing...', response);
        _publish(tb, _findItem(tb.treeData, item.parentID), item,
                 response.data.attributes);
    }else{
        tb.updateFolder(null, _findItem(tb.treeData, item.parentID));
    }
    return {};
}

Fangorn.config.weko = {
    folderIcon: _fangornFolderIcons,
    uploadSuccess: _uploadSuccess,
    itemButtons: _wekoItemButtons,
    resolveRows: _fangornColumns
};

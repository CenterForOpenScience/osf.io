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

// Define Fangorn Button Actions
var _wekoItemButtons = {
    view: function (ctrl, args, children) {
        var buttons = [];
        var tb = args.treebeard;
        var item = args.item;
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

        function createIndex(parent_item, titleJa, titleEn, dismissCallback) {
            console.log('Creating... ' + item + ' - ' + titleJa + ' - ' + titleEn);
            var parentPath = null;
            if(parent_item.kind == 'folder') {
                parentPath = parent_item.data.path;
            }
            $osf.postJSON(
                    item.data.nodeApiUrl + 'weko/indices/',
                    ko.toJS({
                        parent_path: parentPath,
                        title_ja: titleJa,
                        title_en: titleEn
                    })
                ).done(function(item){
                    console.log('Created');
                    item = tb.createItem(item, parent_item.id);
                    item.notify.update('New index created!', 'success',
                                       undefined, 1000);
                    if(dismissCallback) {
                        dismissCallback();
                    }
                });
        }

        if (tb.options.placement !== 'fileview') {
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
        }
        return m('span', buttons);
    }
};

function gotoItem (item) {
    var itemId = /\/item([0-9]+)$/.exec(item.data.path)[1];

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

function _fangornDeleteUrl(item) {
    return waterbutler.buildTreeBeardDelete(item, {full_path: item.data.path + '?' + $.param({name: item.data.name})});
}

function _fangornLazyLoad(item) {
    return waterbutler.buildTreeBeardMetadata(item, {version: item.data.version});
}

function _canDrop(item) {
    return true;
}

function _uploadUrl(item, file) {
    return item.data.nodeApiUrl + 'weko/draft/';
}

function _uploadMethod(item) {
    return 'POST';
}

function _cancelDraft(file, item, response, dismissCallback) {
    console.log('canceled');
    $.ajax({
        url: response.nodeApiUrl + 'weko/draft/' + response.draft_id + '/',
        type: 'DELETE',
        success: function(result) {
            console.log('Deleted');
            console.log(item);

            dismissCallback();
        }
    });
}

function _submitDraft(file, parentItem, response, metadata, dismissCallback) {
    console.log('confirmed');
    console.log(file);
    console.log(metadata);
    console.log(parentItem);
    $osf.putJSON(response.nodeApiUrl + 'weko/draft/' + response.draft_id + '/',
                  ko.toJS({asWEKOExport: metadata.asWEKOExport,
                           filename: file.name,
                           serviceItemType: metadata.serviceItemType,
                           insertIndex: parentItem.data.path})
        ).done(function(item){
            console.log('Created');
            console.log(item);

            dismissCallback();
        });
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

function _uploadSuccess(file, item, response) {
    var tb = this;
    console.log('Retrieving serviceitemtype...');
    $.getJSON(response.nodeApiUrl + 'weko/serviceitemtype').done(function (data) {
        console.log('ServiceItemType loaded');
        var fileDesc = {asWEKOExport: m.prop(false), serviceItemType: m.prop(0)};
        var modalContent = [m('.form-group', [
                               m('label', [
                                   m('input[type=checkbox]',
                                     {onchange: function() {
                                                    fileDesc.asWEKOExport(this.checked);
                                                    $('#service_item_type').prop('disabled', this.checked);
                                                },
                                      disabled: ! response.hasImportXml}),
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
                                _cancelDraft(file, item, response,
                                             function() {
                                                 tb.modal.dismiss();
                                                 tb.updateFolder(null, _findItem(tb.treeData, item.parentID));
                                             });
                            }}, 'Cancel'),
                            m('button.btn.btn-primary', {onclick: function () {
                                _submitDraft(file,
                                             _findItem(tb.treeData, item.parentID),
                                             response,
                                             {asWEKOExport: fileDesc.asWEKOExport(),
                                              serviceItemType: fileDesc.serviceItemType()},
                                             function() {
                                                 tb.modal.dismiss();
                                                 tb.updateFolder(null, _findItem(tb.treeData, item.parentID));
                                             });
                            }}, 'Submit')];
        tb.modal.update(modalContent, modalActions, m('h3.break-word.modal-title', 'Select file type'));
    }).fail(function (xhr, status, error) {
        var statusCode = xhr.responseJSON.code;
        var message = 'Error: Something went wrong when retrieving serviceitemtype. statusCode=' + statusCode;

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
        tb.modal.update(modalContent, modalActions);
    });
    return {};
}

Fangorn.config.weko = {
    folderIcon: _fangornFolderIcons,
    resolveDeleteUrl: _fangornDeleteUrl,
    lazyload:_fangornLazyLoad,
    canDrop: _canDrop,
    uploadUrl: _uploadUrl,
    uploadMethod: _uploadMethod,
    uploadSuccess: _uploadSuccess,
    itemButtons: _wekoItemButtons
};

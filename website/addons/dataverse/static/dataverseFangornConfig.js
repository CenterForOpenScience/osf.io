'use strict';

var m = require('mithril');
var URI = require('URIjs');
var $ = require('jquery');

var Fangorn = require('js/fangorn');
var waterbutler = require('js/waterbutler');
var $osf = require('js/osfHelpers');

function changeState(grid, item, version) {
    item.data.version = version;
    grid.updateFolder(null, item);
}

function _downloadEvent(event, item, col) {
    event.stopPropagation();
    window.location = waterbutler.buildTreeBeardDownload(item, {path: item.data.extra.fileId});
}

// Define Fangorn Button Actions
var _dataverseItemButtons = {
    view: function (ctrl, args, children) {
        var buttons = [];
        var tb = args.treebeard;
        var item = args.item;
        function _uploadEvent(event, item, col) {
            event.stopPropagation();
            tb.dropzone.hiddenFileInput.click();
            tb.dropzoneItemCache = item;
        }
        function dataversePublish(event, item, col) {
            var both = !item.data.dataverseIsPublished;
            var url = item.data.urls.publish;
            var toPublish = both ? 'Dataverse and dataset' : 'dataset';
            var modalContent = [
                m('p.m-md', both ? 'This dataset cannot be published until ' + item.data.dataverse + ' Dataverse is published. ' : ''),
                m('p.m-md', 'By publishing this ' + toPublish + ', all content will be made available through the Harvard Dataverse using their internal privacy settings, regardless of your OSF project settings. '),
                m('p.font-thick.m-md', both ? 'Do you want to publish this Dataverse AND this dataset?' : 'Are you sure you want to publish this dataset?')
            ];
            var modalActions = [
                m('button.btn.btn-default', {
                    'onclick': function () {
                        tb.modal.dismiss();
                    }
                }, 'Cancel'),
                m('button.btn.btn-primary', {
                    'onclick': function () {
                        publishDataset();
                    }
                }, 'Publish')
            ];

            tb.modal.update(modalContent, modalActions, m('h3.break-word.modal-title', 'Publish this ' + toPublish + '?'));

            function publishDataset() {
                tb.modal.dismiss();
                item.notify.update('Publishing ' + toPublish, 'info', 1, 1);
                $.osf.putJSON(
                    url,
                    {'publish_both': both}
                ).done(function (data) {
                    item.notify.update();
                    var modalContent = [
                        m('p.m-md', 'Your content has been published.')
                    ];
                    var modalActions = [
                        m('button.btn.btn-primary', {
                            'onclick': function () {
                                tb.modal.dismiss();
                            }
                        }, 'Got it')

                    ];
                    tb.modal.update(modalContent, modalActions, m('h3.break-word.modal-title', 'Successfully published'));
                    item.data.dataverseIsPublished = true;
                    item.data.hasPublishedFiles = item.children.length > 0;
                    item.data.version = item.data.hasPublishedFiles ? 'latest-published' : 'latest';
                    for (var i = 0; i < item.children.length; i++) { // Brute force the child files to be set as "latest-published" without page reload
                        item.children[i].data.extra.datasetVersion = item.data.version;
                    }
                }).fail(function (xhr, status, error) {
                    var statusCode = xhr.responseJSON.code;
                    var message;
                    switch (statusCode) {
                    case 405:
                        message = 'Error: This dataset cannot be published until ' + item.data.dataverse + ' Dataverse is published.';
                        break;
                    case 409:
                        message = 'This dataset version has already been published.';
                        break;
                    default:
                        message = 'Error: Something went wrong when attempting to publish your dataset.';
                        Raven.captureMessage('Could not publish dataset', {
                            url: url,
                            textStatus: status,
                            error: error
                        });
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
                    tb.modal.update(modalContent, modalActions);
                });
            }
        }
        if (item.data.addonFullname) {
            var options = [
                m('option', {selected: item.data.version === 'latest', value: 'latest'}, 'Draft')
            ];
            if (item.data.dataverseIsPublished) {
                options.push(m('option', {selected: item.data.version === 'latest-published', value: 'latest-published'}, 'Published'));
            }
            buttons.push(
                m.component(Fangorn.Components.dropdown, {
                    'label': 'Version: ',
                    onchange: function (e) {
                        changeState(tb, item, e.target.value);
                    },
                    icon: 'fa fa-external-link',
                    className: 'text-info'
                }, options)
            );
        }
        if (tb.options.placement !== 'fileview') {
            if (item.kind === 'folder' && item.data.addonFullname && item.data.version === 'latest' && item.data.permissions.edit) {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            _uploadEvent.call(tb, event, item);
                        },
                        icon: 'fa fa-upload',
                        className: 'text-success'
                    }, 'Upload'),
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            dataversePublish.call(tb, event, item);
                        },
                        icon: 'fa fa-globe',
                        className: 'text-primary'
                    }, 'Publish')
                );
            } else if (item.kind === 'folder' && !item.data.addonFullname) {
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
                            _downloadEvent.call(tb, event, item);
                        },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download')
                );
                if (item.parent().data.version === 'latest' && item.data.permissions.edit) {
                    buttons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                Fangorn.ButtonEvents._removeEvent.call(tb, event, [item]);
                            },
                            icon: 'fa fa-trash',
                            className: 'text-danger'
                        }, 'Delete')
                    );
                }
                if (item.data.permissions && item.data.permissions.view) {
                    buttons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function(event) {
                                gotoFile(item);
                            },
                            icon: 'fa fa-external-link',
                            className : 'text-info'
                        }, 'View'));

                }
            }
        }
        return m('span', buttons);
    }
};

function gotoFile (item) {
    var redir = new URI(item.data.nodeUrl);
    window.location = redir
        .segment('files')
        .segment(item.data.provider)
        .segment(item.data.extra.fileId)
        .query({version: item.data.extra.datasetVersion})
        .toString();
}

function _fangornDataverseTitle(item, col) {
    var tb = this;
    if (item.data.isAddonRoot && item.connected === false) { // as opposed to undefined, avoids unnecessary setting of this value
        return Fangorn.Utils.connectCheckTemplate.call(this, item);
    }
    var version = item.data.version === 'latest-published' ? 'Published' : 'Draft';
    if (item.data.addonFullname) {
        var contents = [m('dataverse-name', item.data.name + ' (' + version + ')')];
        if (item.data.hasPublishedFiles) {
            if (item.data.permissions.edit) {
                // Default to version in url parameters for file view page
                var urlParams = $osf.urlParams();
                if (urlParams.version && urlParams.version !== item.data.version) {
                    item.data.version = urlParams.version;
                }
            } else {
                contents.push(
                    m('span.text-muted', '[Published]')
                );
            }
        } else {
            contents.push(
                m('span.text.text-muted', '[Draft]')
            );
        }
        return m('span', contents);
    } else {
        return m('span', [
            m('dataverse-name.fg-file-links', {
                onclick: function () {
                    gotoFile(item);
                }
            }, item.data.name
                )
        ]);
    }
}

function _fangornColumns(item) {
    var tb = this;
    var selectClass = '';
    var columns = [];
    columns.push({
        data : 'name',
        folderIcons : true,
        filter : true,
        css: selectClass,
        custom: _fangornDataverseTitle
    });

    if (tb.options.placement === 'project-files') {
        columns.push(
            {
                data: 'downloads',
                filter: false,
                css: ''
            }
        );
    }
    return columns;
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
    return item.data.provider &&
        item.kind === 'folder' &&
        item.data.permissions.edit &&
        item.data.version === 'latest';
}

Fangorn.config.dataverse = {
    folderIcon: _fangornFolderIcons,
    resolveDeleteUrl: _fangornDeleteUrl,
    resolveRows: _fangornColumns,
    lazyload:_fangornLazyLoad,
    canDrop: _canDrop,
    itemButtons: _dataverseItemButtons
};

'use strict';
/**
 * IQB-RIMS FileBrowser configuration module.
 */

var m = require('mithril');
var Fangorn = require('js/fangorn').Fangorn;
var Raven = require('raven-js');
var storageAddons = require('json-loader!storageAddons.json');

var logPrefix = '[iqbrims] ';
var stateRequested = false;
var latestState = null;

// Define Fangorn Button Actions
var _iqbrimsItemButtons = {
    view : function(ctrl, args, children) {
        var tb = args.treebeard;
        var item = args.item;
        var rowButtons = [];
        if (tb.options.placement !== 'fileview') {
            if (item.kind === 'file') {
                rowButtons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) { Fangorn.ButtonEvents._downloadEvent.call(tb, event, item); },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download')
                );
                if (item.data.permissions && item.data.permissions.view) {
                    rowButtons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                Fangorn.ButtonEvents._gotoFileEvent.call(tb, item, '/');
                            },
                            icon: 'fa fa-file-o',
                            className: 'text-info'
                        }, 'View'));
                }
            } else if (item.data.provider) {
                rowButtons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) { Fangorn.ButtonEvents._downloadZipEvent.call(tb, event, item); },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download as zip')
                );
            }
            return m('span', rowButtons);
        }
    }
};

function _iqbrimsTitle(item, col) {
    var tb = this;
    if (item.data.isAddonRoot && item.connected === false) { // as opposed to undefined, avoids unnecessary setting of this value
        return Fangorn.Utils.connectCheckTemplate.call(this, item);
    }
    var contents = [m('iqbrims-name', item.data.name)];
    if (item.data.isAddonRoot) {
        if (!stateRequested) {
            var url = item.data.nodeApiUrl + 'iqbrims/status';
            console.log(logPrefix, 'loading: ', url);
            stateRequested = true;

            return $.ajax({
                url: url,
                type: 'GET',
                dataType: 'json'
            }).done(function (data) {
                console.log(logPrefix, 'loaded: ', data);
                latestState = data['data']['attributes'];
            }).fail(function(xhr, status, error) {
                Raven.captureMessage('Error while retrieving addon info', {
                    extra: {
                        url: url,
                        status: status,
                        error: error
                    }
                });
            });
        }
    } else if (item.kind == 'folder') {
        var state = null;
        if (latestState) {
            var folders = latestState['review_folders'];
            var folderTypes = Object.keys(folders).map(function(k) {
                return [k, folders[k]];
            }).filter(function(e) {
                return e[1] == item.data.name;
            });
            if (folderTypes.length > 0) {
                var key = 'workflow_' + folderTypes[0][0] + '_state';
                if (latestState[key]) {
                    state = latestState[key];
                }
            }
        }
        if (state) {
            contents.push(
                m('span.text-muted', '[' + state + ']')
            );
        }
    }
    return m('span', contents);
}

function _iqbrimsColumns(item) {
    var tb = this;
    var columns = [];
    columns.push({
        data : 'name',
        folderIcons : true,
        filter : true,
        custom: _iqbrimsTitle,
    });
    if (tb.options.placement === 'project-files') {
        columns.push(
        {
            data  : 'size',
            sortInclude : false,
            filter : false,
        });
        columns.push({
            data: 'version',
            filter: false,
            sortInclude : false,
            custom: function() {return m('');}
        });
        columns.push(
        {
            data  : 'downloads',
            sortInclude : false,
            filter : false,
            custom : function() {return m('');}
        });
    }
    if(tb.options.placement !== 'fileview') {
        columns.push({
            data : 'modified',
            filter: false,
        });
    }
    return columns;
}


// Register configuration
Fangorn.config.iqbrims = {
    itemButtons: _iqbrimsItemButtons,
    resolveRows: _iqbrimsColumns,
};

var $ = require('jquery');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var Fangorn = require('js/fangorn');

/**
 * @class FilesWidget
 * Modularized files widget
 * 
 * @param {String} divID id of target div
 * @param {String} filesUrl url to fecth files data for during init
 * @param {Object} opts optional overrides to Treebeard options
 **/ 
var FilesWidget = oop.defclass({
    constructor: function(divID, filesUrl, opts) {
        var self = this;

        self.filesUrl = filesUrl;

        var fangornOpts = {
            divID: divID,
            filesData: filesUrl,
            uploads: true,
            showFilter: true,
            placement: 'dashboard',
            title: undefined,
            filterFullWidth: true, // Make the filter span the entire row for this view
            xhrconfig: $osf.setXHRAuthorization,
            lazyLoadPreprocess: function(data) {
                return data.data;
            },
            columnTitles: function() {
                return [{
                    title: 'Name',
                    width: '90%',
                    sort: true,
                    sortType: 'text'
                }];
            },
            resolveRows: function(item) {
                var tb = this;
                item.css = '';
                if (tb.isMultiselected(item.id)) {
                    item.css = 'fangorn-selected';
                }
                var defaultColumns = [{
                    data: 'name',
                    folderIcons: true,
                    filter: true,
                    custom: Fangorn.DefaultColumns._fangornTitleColumn
                }];
                if (item.parentID) {
                    item.data.permissions = item.data.permissions || item.parent().data.permissions;
                    if (item.data.kind === 'folder') {
                        item.data.accept = item.data.accept || item.parent().data.accept;
                    }
                }
                if (item.data.uploadState && (item.data.uploadState() === 'pending' || item.data.uploadState() === 'uploading')) {
                    return Fangorn.Utils.uploadRowTemplate.call(tb, item);
                }

                var configOption = Fangorn.Utils.resolveconfigOption.call(this, item, 'resolveRows', [item]);
                return configOption || defaultColumns;
            }
        };
        self.fangornOpts = $.extend({}, fangornOpts, opts);
    },
    init: function() {
        var filebrowser = new Fangorn(this.fangornOpts);
    }
});

module.exports = FilesWidget;

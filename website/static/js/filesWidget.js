var $ = require('jquery');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');
var osfLanguage = require('js/osfLanguage');
var Fangorn = require('js/fangorn');

/**
 * @class FilesWidget
 * Modularized files widget
 *
 * @param {String} divID id of target div
 * @param {String} filesUrl url to fecth files data for during init
 * @param {Object} opts optional overrides to Treebeard options
 **/
var FilesWidget = function(divID, filesUrl, opts) {
    var self = this;

    self.filesUrl = filesUrl;

    var fangornOpts = {
        divID: divID,
        filesData: filesUrl,
        uploads: true,
        showFilter: true,
        title: undefined,
        filterFullWidth: true, // Make the filter span the entire row for this view
        xhrconfig: $osf.setXHRAuthorization,
        hScroll: null,
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
};
FilesWidget.prototype.init = function() {
    var self = this;

    return $.ajax({
        url: self.filesUrl
    }).done(function(response) {
        self.fangornOpts.filesData = response.data;
        self.filebrowser = new Fangorn(self.fangornOpts);
    }).fail(function(xhr, status, error) {
        Raven.captureMessage('Could not GET files', {
            url: self.filesUrl,
            textStatus: status,
            error: error
        });
        $('#' + self.fangornOpts.divID).replaceWith(
            $('<div>', {
                'class': 'col-md-12 bg-danger',
                css: {
                    padding: '10px'
                }
            }).append(
                $('<span>', {
                    html: 'Sorry, we could not load files right now. ' + osfLanguage.REFRESH_OR_SUPPORT
                })
            )
        );
    });
};
FilesWidget.prototype.destroy = function() {
    if (this.filebrowser) {
        if (this.filebrowser.grid.tbController) {
            this.filebrowser.grid.tbController.destroy();
            delete this.filebrowser.tbController;
        }
        delete this.filebrowser;
    }
};

module.exports = FilesWidget;

'use strict';

var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');
var $osf = require('osfHelpers');
var bootbox = require('bootbox');
var waterbutler = require('waterbutler');

ko.punches.enableAll();

var Revision = function(data, index, file, node) {

    var ops = {};
    var self = this;

    $.extend(self, data);
    ops[self.versionIdentifier] = self.version;

    self.date = new $osf.FormattableDate(data.modified);
    self.displayDate = self.date.local !== 'Invalid date' ?
        self.date.local :
        data.date;

    // Append modification time to file name if OSF Storage and not current version
    if (file.provider === 'osfstorage' && file.name && index !== 0) {
        var parts = file.name.split('.');
        if (parts.length === 1) {
            ops.displayName = parts[0] + '-' + data.modified;
        } else {
            ops.displayName = parts.slice(0, parts.length - 1).join('') + '-' + data.modified + '.' + parts[parts.length - 1];
        }
    }

    self.osfViewUrl = '?' + $.param(ops);
    self.osfDownloadUrl = '?' + $.param($.extend({action: 'download'}, ops));
    self.waterbutlerDownloadUrl = waterbutler.buildDownloadUrl(file.path, file.provider, node.id, ops);

    self.download = function() {
        window.location = self.waterbutlerDownloadUrl;
        return false;
    };

};

var RevisionsViewModel = function(node, file, editable) {

    var self = this;

    self.node = node;
    self.file = file;
    self.editable = ko.observable(editable);
    self.urls = {
        delete: waterbutler.buildDeleteUrl(file.path, file.provider, node.id, file.extra),
        download: waterbutler.buildDownloadUrl(file.path, file.provider, node.id, file.extra),
        revisions: waterbutler.buildRevisionsUrl(file.path, file.provider, node.id),
    };
    self.errorMessage = ko.observable('');
    self.currentVersion = ko.observable({});
    self.revisions = ko.observableArray([]);
    self.versioningSupported = ko.observable(true);

    self.userColumn = ko.computed(function() {
        return self.revisions()[0] &&
            self.revisions()[0].extra &&
            self.revisions()[0].extra.user;
    });

};

RevisionsViewModel.prototype.fetch = function() {
    var self = this;
    var request = $.getJSON(self.urls.revisions);

    request.done(function(response) {
        self.revisions(ko.utils.arrayMap(response.data, function(item, index) {
            if ($osf.urlParams()[item.versionIdentifier] === item.version) {
                self.currentVersion(new Revision(item, index, self.file, self.node));
                return self.currentVersion();
            }
            return new Revision(item, index, self.file, self.node);
        }));

        if (Object.keys(self.currentVersion()).length === 0) {
            self.currentVersion(self.revisions()[0]);
        }
    });

    request.fail(function(response) {
        self.versioningSupported(false);
        var err = response.responseJSON ?
            response.responseJSON.message || 'Unable to fetch versions' :
            'Unable to fetch versions';

        self.errorMessage(err);

        // Hack for Figshare
        // only figshare will error on a revisions request
        // so dont allow downloads and set a fake current version
        self.editable(false);
        self.currentVersion({
            osfViewUrl: '',
            osfDownloadUrl: '?action=download',
            download: function() {
                window.location = self.urls.download + '&' + $.param({displayName: self.file.name});
                return false;
            }
        });
    });
};

RevisionsViewModel.prototype.delete = function() {
    var self = this;
    $.ajax({
        type: 'DELETE',
        url: self.urls.delete,
    }).done(function() {
        window.location = self.node.urls.files;
    }).fail(function() {
        $osf.growl('Error', 'Could not delete file.');
    });
};

RevisionsViewModel.prototype.askDelete = function() {
    var self = this;
    bootbox.confirm({
        title: 'Delete file?',
        message: '<p class="overflow">' +
                'Are you sure you want to delete <strong>' +
                self.file.safeName + '</strong>?' +
            '</p>',
        callback: function(confirm) {
            if (confirm) {
                self.delete();
            }
        }
    });
};

RevisionsViewModel.prototype.isActive = function(version) {
    var self = this;

    if (self.currentVersion() === version) {
        return 'info';
    }
    return;
};

var RevisionTable = function(selector, node, file, editable) {

    var self = this;

    self.viewModel = new RevisionsViewModel(node, file, editable);
    self.viewModel.fetch();
    $osf.applyBindings(self.viewModel, selector);

};

module.exports = RevisionTable;

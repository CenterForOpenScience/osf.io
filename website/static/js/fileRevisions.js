'use strict';

var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');
var $osf = require('osfHelpers');
var bootbox = require('bootbox');
var waterbutler = require('waterbutler');

ko.punches.enableAll();

var Revision = function(data, file, node) {

    var self = this;

    $.extend(self, data);
    var ops = {};
    ops[self.versionIdentifier] = self.version;

    self.downloadUrl = waterbutler.buildDownloadUrl(file.path, file.provider, node.id, ops);
    self.date = new $osf.FormattableDate(data.modified);
    self.displayDate = self.date.local !== 'Invalid date' ?
        self.date.local :
        data.date;

    self.viewUrl = '?' + $.param(ops);

    ops.action = 'download';
    self.downloadUrl = '?' + $.param(ops);

    self.download = function() {
        window.location = self.downloadUrl;
        return false;
    };


};

var RevisionsViewModel = function(node, file, editable) {

    var self = this;

    self.node = node;
    self.file = file;
    self.editable = editable;
    self.urls = {
        delete: waterbutler.buildDeleteUrl(file.path, file.provider, node.id),
        download: waterbutler.buildDownloadUrl(file.path, file.provider, node.id),
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
        self.revisions(ko.utils.arrayMap(response.data, function(item) {
            if($osf.urlParams()[item.versionIdentifier] === item.version) {
                self.currentVersion(new Revision(item, self.file, self.node));
                return self.currentVersion();
            }
            return new Revision(item, self.file, self.node);
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
                self.file.name + '</strong>?' +
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

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
    self.revisions = ko.observableArray([]);
    self.versioningSupported = ko.observable(true);

};

RevisionsViewModel.prototype.fetch = function() {
    var self = this;
    var request = $.getJSON(self.urls.revisions);

    request.done(function(response) {
        var revisions = ko.utils.arrayMap(response.data, function(item) {
            return new Revision(item, self.file, self.node);
        });

        self.revisions(self.revisions().concat(revisions));
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

RevisionsViewModel.prototype.download = function() {
    var self = this;
    window.location = self.urls.download;
    return false;
};

var RevisionTable = function(selector, node, file, editable) {

    var self = this;

    self.viewModel = new RevisionsViewModel(node, file, editable);
    self.viewModel.fetch();
    $osf.applyBindings(self.viewModel, selector);

};

module.exports = RevisionTable;

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
    self.page = 0;
    self.more = ko.observable(false);
    self.errorMessage = ko.observable('');
    self.revisions = ko.observableArray([]);
    self.versioningSupported = ko.observable(true);

};

RevisionsViewModel.prototype.fetch = function() {
    var self = this;
    var request = $.getJSON(
        self.urls.revisions,
        {page: self.page}
    );

    request.done(function(response) {
        // self.more(response.more);
        var revisions = ko.utils.arrayMap(response.data, function(item) {
            return new Revision(item, self.file, self.node);
        });
        self.revisions(self.revisions().concat(revisions));
        self.page += 1;
    });

    request.fail(function(response) {
        self.versioningSupported(false);
        self.errorMessage(response.responseJSON.message || 'Unable to fetch versions');
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

var RevisionTable = function(selector, node, file, editable) {

    var self = this;

    self.viewModel = new RevisionsViewModel(node, file, editable);
    self.viewModel.fetch();
    $osf.applyBindings(self.viewModel, selector);

};

module.exports = RevisionTable;

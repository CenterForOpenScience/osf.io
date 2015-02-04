'use strict';

var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');
var $osf = require('osfHelpers');
var bootbox = require('bootbox');
var waterbutler = require('waterbutler');

ko.punches.enableAll();

var Revision = function(data) {

    var self = this;

    $.extend(self, data);
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
    self.revisions = ko.observableArray([]);

};

RevisionsViewModel.prototype.fetch = function() {
    var self = this;
    $.getJSON(
        self.urls.revisions,
        {page: self.page}
    ).done(function(response) {
        // self.more(response.more);
        var revisions = ko.utils.arrayMap(response.data, function(item) {
            return new Revision(item);
        });
        self.revisions(self.revisions().concat(revisions));
        self.page += 1;
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
                self.name + '</strong>?' +
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

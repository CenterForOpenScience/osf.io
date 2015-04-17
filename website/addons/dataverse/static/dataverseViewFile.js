/**
 * Simple knockout model and view model for rendering the info table on the
 * file detail page.
 */

'use strict';
var ko = require('knockout');
require('knockout.punches');
var $ = require('jquery');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');

ko.punches.enableAll();

function ViewModel(url) {
    var self = this;
    self.nodeTitle = ko.observable();
    self.filename = ko.observable();
    self.dataverse = ko.observable();
    self.dataverseUrl = ko.observable();
    self.dataset = ko.observable();
    self.datasetUrl = ko.observable();
    self.downloadUrl = ko.observable();
    self.deleteUrl = ko.observable();
    self.filesUrl = ko.observable();
    self.loaded = ko.observable(false);
    self.deleting = ko.observable(false);

    // Note: Dataverse registrations not yet enabled
    self.registered = ko.observable(null);

    $.ajax({
        url: url, type: 'GET', dataType: 'json',
        success: function(response) {
            var data = response.data;
            self.nodeTitle(data.node.title);
            self.filename(data.filename);
            self.dataverse(data.dataverse);
            self.dataverseUrl(data.urls.dataverse);
            self.dataset(data.dataset);
            self.datasetUrl(data.urls.dataset);
            self.downloadUrl(data.urls.download);
            self.deleteUrl(data.urls.delete);
            self.filesUrl(data.urls.files);
            self.loaded(true);
        }
    });

    self.deleteFile = function(){
        bootbox.confirm(
            {
                title: 'Delete Dataverse file?',
                message:'Are you sure you want to delete <strong>' +
                          self.filename() + '</strong> from your Dataverse?',
                callback: function(confirmed) {
                    if (confirmed) {
                        self.deleting(true);
                        var request = $.ajax({
                            type: 'DELETE',
                            url: self.deleteUrl()
                        });
                        request.done(function() {
                            window.location = self.filesUrl();
                        });
                        request.fail(function( jqXHR, textStatus ) {
                            self.deleting(false);
                            $osf.growl( 'Could not delete', textStatus );
                        });
                    }
                }
        });
    };
}

// Public API
function DataverseFileTable(selector, url) {
    this.viewModel = new ViewModel(url);
    $osf.applyBindings(this.viewModel, selector);
}

module.exports = DataverseFileTable;

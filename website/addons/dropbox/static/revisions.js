/**
 * Simple knockout model and view model for rendering the revision table on the
 * file detail page.
 */

'use strict';
var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');
var $osf = require('osfHelpers');
var bootbox = require('bootbox');

ko.punches.enableAll();

function Revision(data) {
    this.rev = data.rev;
    this.modified = new $.osf.FormattableDate(data.modified);
    this.download = data.download;
    this.view = data.view;
}
function RevisionViewModel(url) {
    var self = this;
    self.revisions = ko.observableArray([]);
    self.path = ko.observable('');
    // Hyperlinks
    self.downloadUrl = ko.observable('');
    self.deleteUrl = ko.observable('');
    self.filesUrl = ko.observable('');
    // Get current revision from URL param
    self.currentRevision = $osf.urlParams().rev;
    self.nodeTitle = ko.observable('');
    // Date when this project was registered, or null if not a registration
    // Note: Registering Dropbox content is disabled for now; leaving
    // this code here in case we enable registrations later on.
    // @jmcarp
    self.registered = ko.observable(null);
    $.ajax({
        url: url, type: 'GET', dataType: 'json'
    }).done(function(response) {
        if (response.registered) {
            self.registered(new Date(response.registered));
        }
        // On success, update the revisions observable
        self.revisions(ko.utils.arrayMap(response.result, function(rev) {
            return new Revision(rev);
        }));
        var downloadUrl = response.urls.download;
        var deleteUrl = response.urls.delete;
        var filesUrl = response.urls.files;
        if (self.currentRevision) {  // Append revision ID as query param if applicable
            downloadUrl = downloadUrl + '?rev=' + self.currentRevision;
        }
        self.downloadUrl(downloadUrl);
        self.deleteUrl(deleteUrl);
        self.filesUrl(filesUrl);
        self.path(response.path);
        self.nodeTitle(response.node.title);
    });

    self.deleteFile = function(){
        bootbox.confirm(
            {
                title: 'Delete Dropbox file?',
                message:'Are you sure you want to delete <strong>' +
                          self.path() + '</strong> from your Dropbox?',
                callback: function(confirmed) {
                    if (confirmed) {
                        $('#deletingAlert').addClass('in');
                        var request = $.ajax({
                            type: 'DELETE',
                            url: self.deleteUrl()
                        });
                        request.done(function() {
                            window.location = self.filesUrl();
                        });
                        request.fail(function( jqXHR, textStatus ) {
                            $('#deletingAlert').removeClass('in');
                            $osf.growl( 'Could not delete', textStatus );
                        });
                    }
                }
        });
    };
}
// Public API
function RevisionTable(selector, url) {
    this.viewModel = new RevisionViewModel(url);
    $osf.applyBindings(this.viewModel, selector);
}

module.exports = RevisionTable;


/**
 * Simple knockout model and view model for managing crud addon delete files on the
 * file detail page.
 */

'use strict';
var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');
var $osf = require('osf-helpers');
var bootbox = require('bootbox');

ko.punches.enableAll();

function DeleteFileViewModel(urls) {
    var self = this;

    self.api_url = ko.observable(urls['delete_url']);
    self.files_page_url = ko.observable(urls['files_page_url']);
    self.deleting = ko.observable(false);

    self.deleteFile = function(){
        bootbox.confirm({
            title: 'Delete file?',
            message: 'Are you sure you want to delete this file? It will not be recoverable.',
            callback: function(result) {
                if(result) {
                    self.deleting(true);
                    var request = $.ajax({
                        type: 'DELETE',
                        url: self.api_url()
                    });
                    request.done(function() {
                        window.location = self.files_page_url();
                    });
                    request.fail(function( jqXHR, textStatus ) {
                        self.deleting(false);
                        $osf.growl('Error:', 'Could not delete: ' + textStatus );
                    });

                }
            }
        });
    };
}
// Public API
function DeleteFile(selector, urls) {
    this.viewModel = new DeleteFileViewModel(urls);
    $osf.applyBindings(this.viewModel, selector);
}

module.exports = DeleteFile;

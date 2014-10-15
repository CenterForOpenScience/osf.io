/**
 * Simple knockout model and view model for managing crud addon delete files on the
 * file detail page.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else {
        global.DeleteFile  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';
    ko.punches.enableAll();
    ko.punches.attributeInterpolationMarkup.enable();

    function DeleteFileViewModel(url, delete_url) {
        var self = this;

        self.api_url = ko.observable(delete_url);
        self.files_page_url = ko.observable(null);

        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function(response) {
            self.files_page_url(response.files_page_url);
            if(self.api_url === ''){
                self.api_url(response.delete_url);
            }
        }).fail(
            $.osf.handleJSONError
        );

        self.deleteFile = function(){
            bootbox.confirm({
                title: 'Delete file?',
                message: 'Are you sure you want to delete this file? It will not be recoverable.',
                callback: function(result) {
                    if(result) {
                        $('#deletingAlert').addClass('in');
                        var request = $.ajax({
                            type: 'DELETE',
                            url: self.api_url()
                        });
                        request.done(function() {
                            window.location = self.files_page_url();
                        });
                        request.fail(function( jqXHR, textStatus ) {
                            $('#deletingAlert').removeClass('in');
                            bootbox.alert( 'Could not delete: ' + textStatus );
                        });
                    }
                }
            });
        };
    }
    // Public API
    function DeleteFile(selector, url, delete_url) {
        this.viewModel = new DeleteFileViewModel(url, delete_url);
        $.osf.applyBindings(this.viewModel, selector);
    }

    return DeleteFile;
}));

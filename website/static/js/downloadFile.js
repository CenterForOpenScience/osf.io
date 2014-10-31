/**
 * Simple knockout model and view model for managing crud addon download files on the
 * file detail page.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else {
        global.DownloadFile  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';
    ko.punches.attributeInterpolationMarkup.enable();

    function DownloadFileViewModel(url, downloadURL) {
        var self = this;

        self.downloadURL = ko.observable(downloadURL);

        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function(response) {
            if(self.downloadURL === ''){
                self.downloadURL(response.downloadURL);
            }
        }).fail(
            $.osf.handleJSONError
        );
    }
    // Public API
    function DownloadFile(selector, url, downloadURL) {
        this.viewModel = new DownloadFileViewModel(url, downloadURL);
        $.osf.applyBindings(this.viewModel, selector);
    }

    return DownloadFile;
}));

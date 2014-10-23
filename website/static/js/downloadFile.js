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
    ko.punches.enableAll();
    ko.punches.attributeInterpolationMarkup.enable();

    function DownloadFileViewModel(url, download_url) {
        var self = this;

        self.download_url = ko.observable(download_url);

        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function(response) {
            if(self.download_url === ''){
                self.download_url(response.download_url);
            }
        }).fail(
            $.osf.handleJSONError
        );
    }
    // Public API
    function DownloadFile(selector, url, download_url) {
        this.viewModel = new DownloadFileViewModel(url, download_url);
        $.osf.applyBindings(this.viewModel, selector);
    }

    return DownloadFile;
}));

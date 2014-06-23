/**
 * Simple knockout model and view model for rendering the info table on the
 * file detail page.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else {
        global.VersionTable  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';
    ko.punches.enableAll();
    ko.punches.attributeInterpolationMarkup.enable();

    function Version(data) {
        this.dataverse = data.dataverse;
        this.dataverse_url = data.dataverse_url;
        this.study = data.study;
        this.study_url = data.study_url;
        this.download_url = data.download_url;
    }
    function VersionViewModel(url) {
        var self = this;
        self.versions = ko.observableArray([]);

        // Date when this project was registered, or null if not a registration
        self.registered = ko.observable(null);
        $.ajax({
            url: url, type: 'GET', dataType: 'json',
            // On success, update the versions observable
            success: function(response) {
                self.versions([new Version(response.data)]);
            }
        });
    }
    // Public API
    function VersionTable(selector, url) {
        this.viewModel = new VersionViewModel(url);
        $.osf.applyBindings(this.viewModel, selector);
    }

    return VersionTable;
}));
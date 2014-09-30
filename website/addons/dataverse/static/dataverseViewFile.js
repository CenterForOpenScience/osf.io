/**
 * Simple knockout model and view model for rendering the info table on the
 * file detail page.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'knockoutpunches'], factory);
    } else if (typeof $script === 'function') {
        global.DataverseFileTable = factory(ko, jQuery, window);
        $script.done('dataverseFileTable');
    } else {
        global.DataverseFileTable  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';
    ko.punches.enableAll();
    ko.punches.attributeInterpolationMarkup.enable();

    function ViewModel(url) {
        var self = this;
        self.dataverse = ko.observable();
        self.dataverse_url = ko.observable();
        self.study = ko.observable();
        self.study_url = ko.observable();
        self.download_url = ko.observable();

        self.loaded = ko.observable(false);

        // Note: Dataverse registrations not yet enabled
        self.registered = ko.observable(null);

        $.ajax({
            url: url, type: 'GET', dataType: 'json',
            success: function(response) {
                var data = response.data;
                self.dataverse(data.dataverse);
                self.dataverse_url(data.dataverse_url);
                self.study(data.study);
                self.study_url(data.study_url);
                self.download_url(data.download_url);
                self.loaded(true);
            }
        });
    }

    // Public API
    function DataverseFileTable(selector, url) {
        this.viewModel = new ViewModel(url);
        $.osf.applyBindings(this.viewModel, selector);
    }

    return DataverseFileTable;
}));
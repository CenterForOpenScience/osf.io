
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'knockoutpunches'], factory);
    } else if (typeof $script === 'function') {
        global.DataverseWidget = factory(ko, jQuery, window);
        $script.done('dataverseWidget');
    } else {
        global.DataverseWidget  = factory(ko, jQuery, window);
    }
}(this, function(ko, $, window) {

    'use strict';
    ko.punches.attributeInterpolationMarkup.enable();

    function ViewModel(url) {
        var self = this;
        self.dataverse = ko.observable();
        self.dataverseUrl = ko.observable();
        self.study = ko.observable();
        self.doi = ko.observable();
        self.studyUrl = ko.observable('');
        self.citation = ko.observable('');
        self.loaded = ko.observable(false);

        self.init = function() {
            $.ajax({
                url: url, type: 'GET', dataType: 'json',
                success: function(response) {
                    var data = response.data;
                    self.dataverse(data.dataverse);
                    self.dataverseUrl(data.dataverseUrl);
                    self.study(data.study);
                    self.doi(data.doi);
                    self.studyUrl(data.studyUrl);
                    self.citation(data.citation);
                    self.loaded(true);
                }
            });
        };
    }

    // Public API
    function DataverseWidget(selector, url) {
        var self = this;
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, selector);
        self.viewModel.init();
    }

    return DataverseWidget;
}));
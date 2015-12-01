
var $ = require('jquery');
var AddonHelper = require('js/addonHelper');


/**
 * Module that controls the Dryad Service node settings. Includes Knockout view-model
 * for syncing data.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'knockoutpunches'], factory);
    } else {
        global.DryadNodeConfig  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    // Enable knockout punches
    ko.punches.enableAll();

    var ViewModel = function(url) {
        var self = this;
        self.url = url;
        // TODO: Initialize observables, computes, etc. here
        self.nodeHasAuth = ko.observable(false);
        self.userHasAuth = ko.observable(false);
        // Flashed messages
        self.message = ko.observable('');

        // Get data from the config GET endpoint
        function onFetchSuccess(response) {
            // Update view model
            self.nodeHasAuth(response.result.nodeHasAuth);
            self.userHasAuth(resposne.result.userHasAuth);
        }
        function onFetchError(xhr, textstatus, error) {
            self.message('Could not fetch settings.');
        }
        function fetch() {
            $.ajax({url: self.url, type: 'GET', dataType: 'json',
                    success: onFetchSuccess,
                    error: onFetchError
            });
        }


    };

    function DryadNodeConfig(selector, url) {
        // Initialization code
        var self = this;
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, selector);
    }

}));

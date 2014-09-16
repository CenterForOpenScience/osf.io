/**
 * Module that controls the Application node settings. Includes Knockout view-model
 * for syncing data.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'knockoutpunches'], factory);
    } else {
        global.AppNodeConfig  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    // Enable knockout punches
    ko.punches.enableAll();

    var ViewModel = function(url) {
        var self = this;
        self.url = url;
        // TODO: Initialize observables, computes, etc. here
        self.customRoutes = ko.observableArray([]);
        // Flashed messages
        self.message = ko.observable('');
        self.customUrl = ko.observable('');
        self.customQuery = ko.observable('');

        self.createCustomRoute = function() {
            $.osf.postJSON(self.url, {route: self.customUrl(),  query: self.customQuery()}, function(resp) {
                self.customRoutes.push({url: self.customUrl(),  query: self.customQuery()});
                self.customUrl('');
                self.customQuery('');
            });
        };

        // Get data from the config GET endpoint
        function onFetchSuccess(response) {
            // Update view model
            self.customRoutes(ko.utils.arrayMap(Object.keys(response), function(key) {
                return {
                    url: key,
                    query: response[key]
                };
            }));

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

        fetch();
    };

    function AppNodeConfig(selector, url) {
        // Initialization code
        var self = this;
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, selector);
    }

    return AppNodeConfig

}));

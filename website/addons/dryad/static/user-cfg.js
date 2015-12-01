

/**
 * Module that controls the Dryad Service user settings. Includes Knockout view-model
 * for syncing data.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'knockoutpunches'], factory);
    } else {
        global.DryadUserConfig  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    // Enable knockout punches
    ko.punches.enableAll();


    var ViewModel = function(url) {
        var self = this;
        self.userHasAuth = ko.observable(false);
        // TODO: Observables, computes, etc. here
    };

    function DryadNodeConfig(selector, url) {
        // Initialization code
        var self = this;
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, selector);
    }

}));

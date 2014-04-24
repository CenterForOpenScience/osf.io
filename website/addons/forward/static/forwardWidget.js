;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'knockoutpunches'], factory);
    } else if (typeof $script === 'function') {
        global.ForwardWidget = factory(ko, jQuery);
        $script.done('forwardWidget');
    } else {
        global.ForwardWidget = factory(ko, jQuery);
    }
}(this, function(ko, $) {

    'use strict';

    // Alias `this` for redirect in view model below; h/t @sloria
    var global = this;

    ko.punches.attributeInterpolationMarkup.enable();

    /**
     * Knockout view model for the Forward node settings widget.
     */
    var ViewModel = function(url) {

        var self = this;

        self.url = ko.observable();
        self.redirectBool = ko.observable();
        self.redirectSecs = ko.observable();

        self.interval = null;
        self.redirecting = ko.observable();
        self.timeLeft = ko.observable();

        self.doRedirect = function() {
            global.location.href = self.url();
        };

        self.tryRedirect = function() {
            if (self.timeLeft() > 0) {
                self.timeLeft(self.timeLeft() - 1);
            } else {
                self.doRedirect();
            }
        };

        self.queueRedirect = function() {
            self.redirecting(true);
            $.blockUI({message: $('#forwardModal')});
            self.timeLeft(self.redirectSecs());
            self.interval = setInterval(
                self.tryRedirect,
                1000
            )
        };

        self.cancelRedirect = function() {
            self.redirecting(false);
            $.unblockUI();
            clearInterval(self.interval);
        };

        self.execute = function() {
            if (self.redirectBool()) {
                self.queueRedirect();
            }
        };

        self.init = function() {
            $.ajax({
                type: 'GET',
                url: url,
                dataType: 'json',
                success: function(response) {
                    self.url(response.url);
                    self.redirectBool(response.redirectBool);
                    self.redirectSecs(response.redirectSecs);
                    self.execute();
                }
            });
        };

    };

    // Public API
    function ForwardWidget(selector, url) {
        var self = this;
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, selector);
        self.viewModel.init();
    }

    return ForwardWidget;

}));

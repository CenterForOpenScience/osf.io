;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else {
        global.NotificationsConfig = factory(ko, jQuery);
        $script.done('NotificationsConfig');
    }
}(this, function(ko, $) {
    'use strict';
    ko.punches.enableAll();

    var ViewModel = function(subscribeInfo) {
        var self = this;
        self.subscribed = ko.observable(subscribeInfo['Open Science Framework General']);
        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-success');

        /** Change the flashed status message */
        self.changeMessage = function(text, css, timeout) {
            self.message(text);
            var cssClass = css || 'text-info';
            self.messageClass(cssClass);
            if (timeout) {
                // Reset message after timeout period
                setTimeout(function() {
                    self.message('');
                    self.messageClass('text-info');
                }, timeout);
            }
        };

        self.submit = function () {
            var request = $.osf.postJSON('/api/v1/settings/notifications/', {'Open Science Framework General': self.subscribed()});
            request.done(function () {
                self.changeMessage('Settings updated.', 'text-success', 5000);
            });
            request.fail(function () {
                var message = 'Could not update settings.';
                self.changeMessage(message, 'text-danger', 5000);

            });
        };
    };

    // API
    function NotificationsViewModel(selector, subscribeInfo) {
        var self = this;
        self.viewModel = new ViewModel(subscribeInfo);
        $.osf.applyBindings(self.viewModel, selector);
    }

    return NotificationsViewModel;

}));
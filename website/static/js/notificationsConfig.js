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

    var ViewModel = function() {
        var self = this;
        self.list = 'Open Science Framework General';
        self.subscribed = ko.observable();
        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-success');

        self.getListInfo = function() {
            $.ajax({
                    url: '/api/v1/settings/notifications',
                    type: 'GET',
                    dataType: 'json',
                    success: function(response) {
                        self.subscribed(response['mailing_lists'][self.list]);
                },
                error: function() {
                    var message = 'Could not retrieve settings information.';
                    self.changeMessage(message, 'text-danger', 5000);
                }});
        };

        self.getListInfo();

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
            request.fail(function (xhr) {
                if (xhr.responseJSON.error_type !== 'not_subscribed') {
                    var message = 'Could not subscribe to ' + self.list + ' at this time. If this issue persists, '
                        + 'please report it to <a href="mailto:support@osf.io">support@osf.io</a>.';
                    self.changeMessage(message, 'text-danger', 5000);
                }
            });
        };
    };

    // API
    function NotificationsViewModel(selector) {
        var self = this;
        self.viewModel = new ViewModel();
        $.osf.applyBindings(self.viewModel, selector);
    }

    return NotificationsViewModel;

}));
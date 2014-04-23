;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'knockoutpunches'], factory);
    } else if (typeof $script === 'function') {
        global.ForwardConfig  = factory(ko, jQuery);
        $script.done('forwardConfig');
    } else {
        global.ForwardConfig = factory(ko, jQuery);
    }
}(this, function(ko, $) {

    'use strict';

    ko.punches.attributeInterpolationMarkup.enable();

    var MESSAGE_TIMEOUT = 5000;
    var MIN_FORWARD_TIME = 5;
    var MAX_FORWARD_TIME = 60;

    var DEFAULT_FORWARD_BOOL = true;
    var DEFAULT_FORWARD_TIME = 15;

    /**
     * Knockout view model for the Forward node settings widget.
     */
    var ViewModel = function(url) {

        var self = this;

        self.boolOptions = [true, false];
        self.boolLabels = {
            true: 'Yes',
            false: 'No'
        }

        // Forward configuration
        self.url = ko.observable().extend({
            required: true,
            // From https://gist.github.com/searls/1033143
            pattern: /\b((?:https?:\/\/|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}\/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))/i
        });
        self.redirectBool = ko.observable(DEFAULT_FORWARD_BOOL);
        self.redirectSecs = ko.observable(DEFAULT_FORWARD_TIME).extend({
            required: true,
            min: MIN_FORWARD_TIME,
            max: MAX_FORWARD_TIME
        });

        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');

        self.validators = ko.validatedObservable({
            url: self.url,
            redirectBool: self.redirectBool,
            redirectSecs: self.redirectSecs
        });

        self.getBoolLabel = function(item) {
            return self.boolLabels[item];
        };

        /**
         * Update the view model from data returned from the server.
         */
        self.updateFromData = function(data) {
            self.url(data.url);
            self.redirectBool(data.redirectBool);
            self.redirectSecs(data.redirectSecs);
        };

        self.fetchFromServer = function() {
            $.ajax({
                type: 'GET',
                url: url,
                dataType: 'json',
                success: function(response) {
                    self.updateFromData(response);
                },
                error: function(xhr, textStatus, error) {
                    console.error(textStatus);
                    console.error(error);
                    self.changeMessage('Could not retrieve Forward settings at ' +
                        'this time. Please refresh ' +
                        'the page. If the problem persists, email ' +
                        '<a href="mailto:support@cos.io">support@cos.io</a>.',
                        'text-warning');
                }
            });
        };

        // Initial fetch from server
        self.fetchFromServer();

        function onSubmitSuccess() {
            self.changeMessage(
                'Successfully linked to <a href="' + self.url() + '">' + self.url() + '</a>.',
                'text-success',
                MESSAGE_TIMEOUT
            );
        }

        function onSubmitError() {
            self.changeMessage(
                'Could not change settings. Please try again later.',
                'text-danger'
            );
        }

        /**
         * Submit new settings.
         */
        self.submitSettings = function() {
            $.osf.putJSON(
                url,
                ko.toJS(self),
                onSubmitSuccess,
                onSubmitError
            );
        };

        /** Change the flashed message. */
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

    };

    // Public API
    function ForwardConfig(selector, url) {
        var self = this;
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, selector);
    }

    return ForwardConfig;

}));

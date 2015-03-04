/**
*
*/
'use strict';

var ko = require('knockout');
require('knockout-validation');
require('knockout-punches');
var $ = require('jquery');

var $osf = require('osfHelpers');

ko.punches.enableAll();

var ViewModel = function(submitUrl) {

    var self = this;

    self.fullName = ko.observable('').extend({
        required: true,
        minLength: 3
    });
    self.email1 = ko.observable('').extend({
        required: true,
        email: true
    });
    self.email2 = ko.observable('').extend({
        required: true,
        email: true,
        validation: {
            validator: function(val, other) {
                return val === other;
            },
            'message': 'Email addresses must match.',
            params: self.email1
        }
    });
    self.password = ko.observable('').extend({
        required: true,
        minLength: 6,
        maxLength: 35
    });

    // Preserve object of validated fields for use in `submit`
    var validatedFields = {
        fullName: self.fullName,
        email1: self.email1,
        email2: self.email2,
        password: self.password
    };
    // Collect validated fields
    self.validatedFields = ko.validatedObservable($.extend({}, validatedFields));

    self.showValidation = ko.observable(false);
    self.submitted = ko.observable(false);

    self.flashMessage = ko.observable();
    self.flashMessageClass = ko.observable();
    self.flashTimeout = null;

    self.trim = function(observable) {
        observable($.trim(observable()));
    };

    /** Change the flashed message. */
    self.changeMessage = function(message, messageClass, text, css, timeout, timeoutClock) {
        message(text);
        var cssClass = css || 'text-info';
        messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            if (timeoutClock) {
                clearTimeout(timeoutClock);
            }
            self.timeout = setTimeout(
                function() {
                    message('');
                    messageClass('text-info');
                },
                timeout
            );
        }
    };

    self.isValid = ko.computed(function() {
        return self.validatedFields.isValid();
    });

    self.submitSuccess = function(response) {
        self.changeMessage(
            self.flashMessage,
            self.flashMessageClass,
            response.message,
            'text-info'
        );
        self.submitted(true);
    };

    self.submitError = function(xhr) {
        self.changeMessage(
            self.flashMessage,
            self.flashMessageClass,
            xhr.responseJSON.message_long,
            'text-danger',
            5000,
            self.flashTimeout
        );
    };

    self.hideValidation = function() {
        self.showValidation(false);
    };

    self.submit = function() {
        // Show errors if invalid
        if (!self.isValid()) {
            // Ensure validation errors are displayed
            $.each(validatedFields, function(key, value) {
                value.notifySubscribers();
            });
            self.showValidation(true);
            return;
        }
        // Else submit
        $osf.postJSON(
            submitUrl,
            ko.toJS(self)
        ).done(
            self.submitSuccess
        ).fail(
            self.submitError
        );
    };

};

var SignUp = function(selector, submitUrl) {
    this.viewModel = new ViewModel(submitUrl);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = SignUp;

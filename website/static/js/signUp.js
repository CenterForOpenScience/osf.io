'use strict';

var ko = require('knockout');
require('knockout.validation');
var $ = require('jquery');

var $osf = require('./osfHelpers');


var ViewModel = function(submitUrl, campaign) {

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
                return String(val).toLowerCase() === String(other).toLowerCase();
            },
            'message': 'Email addresses must match.',
            params: self.email1
        }
    });
    self.password = ko.observable('').extend({
        required: true,
        minLength: 6,
        maxLength: 256
    });
    self.campaign = ko.observable(campaign);

    // Preserve object of validated fields for use in `submit`
    var validatedFields = {
        fullName: self.fullName,
        email1: self.email1,
        email2: self.email2,
        password: self.password
    };
    // Collect validated fields
    self.validatedFields = ko.validatedObservable($.extend({}, validatedFields));

    self.submitted = ko.observable(false);

    self.flashMessage = ko.observable('');
    self.flashMessageClass = ko.observable('');
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
                    messageClass('');
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
            'text-info p-xs'
        );
        self.submitted(true);
    };

    self.submitError = function(xhr) {
        self.changeMessage(
            self.flashMessage,
            self.flashMessageClass,
            xhr.responseJSON.message_long,
            'text-danger p-xs',
            5000,
            self.flashTimeout
        );
    };

    self.submit = function() {
        if (self.submitted()) {
            $osf.growl('Already submitted', 'You cannot sign up more than once.');
            return false;
        }
        // Show errors if invalid
        if (!self.isValid()) {
            // Ensure validation errors are displayed
            $.each(validatedFields, function(key, value) {
                value.notifySubscribers();
            });
            return false;
        }
        // Else submit, and send Google Analytics event
        window.ga('send', 'event', 'signupSubmit', 'click', 'new_user_submit');
        $osf.postJSON(
            submitUrl,
            ko.toJS(self)
        ).done(
            self.submitSuccess
        ).fail(
            self.submitError
        );
    };

    self.errors = ko.validation.group(self);

};

var SignUp = function(selector, submitUrl, campaign) {
    this.viewModel = new ViewModel(submitUrl, campaign);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = SignUp;

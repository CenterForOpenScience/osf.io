'use strict';

var ko = require('knockout');
require('knockout.validation');
var $ = require('jquery');
var zxcvbn = require('zxcvbn');

var $osf = require('./osfHelpers');


// Accepts a few different types of arguments, depending on
// the desired fields and type of password reset.
// types:
//    - signup: required fields for Name, email, email confirmation, password, and password strength
//    - reset: fields for password, strength, and password confirmation
var ViewModel = function(passwordViewType, submitUrl, campaign) {

    var self = this;

    self.typedPassword = ko.observable('');

    self.passwordInfo = ko.computed(function() {
        if (self.typedPassword()) {
            return zxcvbn(self.typedPassword());
        }
    });

    self.passwordFeedback = ko.computed(function () {
        if (self.typedPassword()) {
            return self.passwordInfo().feedback.warning;
        }
    });

    self.passwordComplexity = ko.pureComputed(function() {
        if (self.typedPassword()) {
            return self.passwordInfo().score;
        }
    });

    self.passwordComplexityBar = ko.computed(function() {
        return $osf.valueProgressBar(self.passwordComplexity());
    });

    self.password = ko.observable('').extend({
        required: true,
        minLength: 6,
        maxLength: 256,
        complexity: 2,
    });

    self.campaign = ko.observable(campaign);

    // Preserve object of validated fields for use in `submit`
    var validatedFields = {
        password: self.password
    };

    if (passwordViewType === 'reset') {
        self.passwordConfirmation = ko.observable('').extend({
            required: true,
            validation: {
                validator: function(val, other) {
                    return String(val).toLowerCase() === String(other).toLowerCase();
                },
                'message': 'Passwords must match.',
                params: self.password
            }
        });
    }

    // only include the following fields if the user is
    // signing up for the first time
    if (passwordViewType === 'signup') {

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

        self.password.extend({notEqual: self.email1});

        validatedFields.fullName = self.fullName;
        validatedFields.email1 = self.email1;
        validatedFields.eamil2 = self.email2;

    }

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
        // Show errors if invalid
        if (!self.isValid()) {
            // Ensure validation errors are displayed
            $.each(validatedFields, function(key, value) {
                value.notifySubscribers();
            });
            return false;
        }
        // If it's a new signup, send Google Analytics event
        if (passwordViewType === 'signup') {
            window.ga('send', 'event', 'signupSubmit', 'click', 'new_user_submit');
        }
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

var SetPassword = function(selector, passwordViewType, submitUrl, campaign) {
    this.viewModel = new ViewModel(passwordViewType, submitUrl, campaign);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = SetPassword;

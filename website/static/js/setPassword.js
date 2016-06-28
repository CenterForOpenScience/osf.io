'use strict';

var ko = require('knockout');
require('knockout.validation');
var $ = require('jquery');
var zxcvbn = require('zxcvbn');

var $osf = require('./osfHelpers');


ko.validation.rules.complexity = {
    validator: function (val, minimumComplexity) {
        return zxcvbn(val).score >= minimumComplexity;
    },
    message: 'Please enter a more complex password.'
};

ko.validation.registerExtenders();

/**
  * Return CSS colors and percentage of a progress bar based on a value.
  * Used to return a value for password complexity
  */
var valueProgressBar = {
    0: {'attr': {'style': 'width: 0%'}, 'text': '', 'text_attr':{}},
    1: {'attr': {'class': 'progress-bar progress-bar-sm progress-bar-danger', 'style': 'width: 20%'}, 'text': 'Very weak', 'text_attr': {'style': 'color: grey'}},
    2: {'attr': {'class': 'progress-bar progress-bar-sm progress-bar-danger', 'style': 'width: 40%'}, 'text': 'Weak', 'text_attr': {'style': 'color: orangered '}},
    3: {'attr': {'class': 'progress-bar progress-bar-sm progress-bar-warning', 'style': 'width: 60%'}, 'text': 'So-so', 'text_attr': {'style': 'color: gold'}},
    4: {'attr': {'class': 'progress-bar progress-bar-sm progress-bar-success', 'style': 'width: 80%; background-image: none; background-color: lawngreen'}, 'text': 'Good', 'text_attr': {'style': 'color: lawngreen'}},
    5: {'attr': {'class': 'progress-bar progress-bar-sm progress-bar-success', 'style': 'width: 100%'}, 'text': 'Great!', 'text_attr': {'style': 'color: limegreen'}}
};

// Accepts a few different types of arguments, depending on
// the desired fields and type of password reset.
// types:
//    - signup: required fields for Name, email, email confirmation, password, and password strength
//    - reset: fields for password, strength, and password confirmation (for when you don't know your old password)
//    - change: change your password when you know your old one
var ViewModel = function(passwordViewType, submitUrl, campaign, redirectUrl) {

    var self = this;

    self.typedPassword = ko.observable('');

    self.passwordInfo = ko.pureComputed(function() {
        if (self.typedPassword()) {
            return zxcvbn(self.typedPassword().slice(0, 100));
        }
    });

    self.passwordFeedback = ko.pureComputed(function () {
        if (self.typedPassword()) {
            return self.passwordInfo().feedback;
        }
    });

    self.passwordComplexity = ko.pureComputed(function() {
        if (self.typedPassword()) {
            return self.passwordInfo().score + 1;
        } else {
            return 0;
        }
    });

    self.passwordComplexityInfo = ko.computed(function() {
        return valueProgressBar[self.passwordComplexity()];
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

    if (passwordViewType === 'reset' || passwordViewType === 'change') {
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

    if (passwordViewType === 'change') {
        self.oldPassword = ko.observable('').extend({
            required: true
        });

        validatedFields.oldPassword = self.oldPassword;
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

        self.password.extend({
            validation: {
                validator: function(val, other) {
                    if (String(val).toLowerCase() === String(other).toLowerCase()) {
                        self.typedPassword(' ');
                        return false;
                    } else {
                        return true;
                    }
                },
                'message': 'Your password cannot be the same as your email address.',
                params: self.email1
            }
        });

        validatedFields.fullName = self.fullName;
        validatedFields.email1 = self.email1;
        validatedFields.email2 = self.email2;

    }

    // pick up the email from contextVars if we can't get it from first typing it in
    if (window.contextVars.username) {
        self.email1 = ko.observable(window.contextVars.username);
    }

    // If we have gotten an email to compare to at this point, also validate against that
    if (self.email1) {
        self.password.extend({
            validation: {
                validator: function(val, other) {
                    if (String(val).toLowerCase() === String(other).toLowerCase()) {
                        self.typedPassword(' ');
                        return false;
                    } else {
                        return true;
                    }
                },
                'message': 'Your password cannot be the same as your username.',
                params: self.email1
            }
        });
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
            'ext-success p-xs'
        );
        if (redirectUrl) {
            setTimeout(function(){ window.location = redirectUrl; }, 3000);
        }
        self.submitted(true);
    };

    self.submitError = function(xhr) {
        if (xhr.status === 400) {
            self.changeMessage(
                self.flashMessage,
                self.flashMessageClass,
                'Your username cannot be the same as your password.',
                'text-danger p-xs',
                5000,
                self.flashTimeout
            );
        } else {
            self.changeMessage(
                self.flashMessage,
                self.flashMessageClass,
                xhr.responseJSON.message_long,
                'text-danger p-xs',
                5000,
                self.flashTimeout
            );
        }
    };

    self.submit = function() {
        if (self.submitted()) {
            self.changeMessage(self.flashMessage, self.flashMessageClass, 'You have already submitted. You cannot sign up more than once.', 'text-danger p-xs');
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

var SetPassword = function(selector, passwordViewType, submitUrl, campaign, redirectUrl) {
    this.viewModel = new ViewModel(passwordViewType, submitUrl, campaign, redirectUrl);
    $osf.applyBindings(this.viewModel, selector);
            $(selector).keypress(
                event => {
                    // If the enter key is pressed to submit a form, check if the password is valid
                    if (event.which == '13') {
                        if (!this.viewModel.password.isValid()) {
                            return false;
                        }
                    }
                }
        );
};

module.exports = SetPassword;

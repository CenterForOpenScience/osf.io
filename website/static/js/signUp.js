'use strict';

var ko = require('knockout');
require('knockout.validation');
var $ = require('jquery');

var $osf = require('./osfHelpers');
var zxcvbn = require('zxcvbn');


var ViewModel = function(submitUrl, campaign) {

    var self = this;

    ko.validation.rules.complexity = {
        validator: function (val, minimumComplexity) {
            return self.passwordComplexity() >= minimumComplexity;
        },
        message: 'Please enter a more complex password.'
    };

    ko.validation.registerExtenders();

    self.typedPassword = ko.observable('');

    self.passwordFeedback = ko.observable('');

    self.passwordComplexity = ko.pureComputed(function() {
        var current = zxcvbn(self.typedPassword());
        self.passwordFeedback(current.feedback.warning);
        return current.score;
    });

    self.passwordComplexityBar = ko.computed(function() {
        if (self.typedPassword()) {
            if (self.passwordComplexity() === 0) {
                return {
                    class: 'progress-bar progress-bar-danger',
                    style: 'width: 10%'
                };
            }
            if (self.passwordComplexity() === 1) {
                return {
                    class: 'progress-bar progress-bar-danger',
                    style: 'width: 25%'
                };
            } else if (self.passwordComplexity() === 2) {
                return {
                    class: 'progress-bar progress-bar-warning',
                    style: 'width: 50%'
                };
            } else if (self.passwordComplexity() === 3) {
                return {
                    class: 'progress-bar progress-bar-warning',
                    style: 'width: 75%'
                };
            } else if (self.passwordComplexity() === 4) {
                return {
                    class: 'progress-bar progress-bar-success',
                    style: 'width: 100%'
                };
            }
        }
    });

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
        maxLength: 256,
        complexity: 2,
        notEqual: self.email1
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

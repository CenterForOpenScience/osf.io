'use strict';

var ko = require('knockout');
require('knockout.validation');
var $ = require('jquery');
var zxcvbn = require('zxcvbn');

var oop = require('js/oop');
var $osf = require('./osfHelpers');
require('js/knockoutPassword')


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

/**
 * Base view model for other password-setting view-models. Stores password input
 * with password verification.
 */
var BaseViewModel = oop.defclass({
    constructor: function () {
        var self = this;
        self.typedPassword = ko.observable('').extend({passwordChecking: true});
        self.passwordFeedback = self.typesPassword.passwordFeedback;

        self.passwordComplexityInfo = ko.computed(function() {
            return valueProgressBar[self.typedPassword.passwordComplexity()];
        });

        self.password = ko.observable('').extend({
            required: true,
            minLength: 6,
            maxLength: 256,
            complexity: 2,
        });


        // Preserve object of validated fields for use in `submit`
        var validatedFields = {
            password: self.password
        };

        // Collect validated fields
        self.validatedFields = ko.validatedObservable($.extend({}, validatedFields, self.getValidatedFields()));

        self.submitted = ko.observable(false);

        // TODO: Use changeMessage.js
        self.flashMessage = ko.observable('');
        self.flashMessageClass = ko.observable('');

        self.trim = function(observable) {
            observable($.trim(observable()));
        };

        /** Change the flashed message. */
        self.changeMessage = function(message, className, timeout) {
            self.flashMessage(message);
            var cssClass = className || 'text-info';
            self.flashMessageClass(cssClass);
            if (timeout) {
                setTimeout(
                    function() {
                        self.flashMessage('');
                        self.flashMessageClass('');
                    },
                    timeout
                );
            }
        };

        self.isValid = ko.computed(function() {
            return self.validatedFields.isValid();
        });

        self.errors = ko.validation.group(self);

    },
    /**
     * Hook to add validated observables to the validation group.
     */
    getValidatedFields: function() {
        return {};
    }
});


var ChangePasswordViewModel = oop.extend(BaseViewModel, {
    constructor: function () {
        var self = this;
        self.super.constructor.call(this);
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
        self.oldPassword = ko.observable('').extend({required: true});
    },
    getValidatedFields: function() {
        var self = this;
        return {
            oldPassword: self.oldPassword
        };
    }
});


var SetPasswordViewModel = oop.extend(BaseViewModel, {
    constructor: function () {
        var self = this;
        self.super.constructor.call(this);
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
});

var SignUpViewModel = oop.extend(BaseViewModel, {
    constructor: function (submitUrl) {
        var self = this;
        self.super.constructor.call(this, submitUrl);
        self.fullName = ko.observable('').extend({
            required: true,
            minLength: 3
        });
        // pick up the email from contextVars if we can't get it from first typing it in
        self.email1 = ko.observable(window.contextVars.username || '').extend({
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

    },
    getValidatedFields: function() {
        var self = this;
        return {
            fullName: self.fullName,
            email1: self.email1,
            email2: self.email2
        };
    },
    submitSuccess: function(response) {
        var self = this;
        self.changeMessage(
            response.message,
            'ext-success p-xs'
        );
        self.submitted(true);
    },

    submitError: function(xhr) {
        var self = this;
        if (xhr.status === 400) {
            self.changeMessage(
                'Your username cannot be the same as your password.',
                'text-danger p-xs',
                5000
            );
        } else {
            self.changeMessage(
                xhr.responseJSON.message_long,
                'text-danger p-xs',
                5000
            );
        }
    },
    submit: function() {
        var self = this;
        var submitUrl = '/api/v1/register/';
        if (self.submitted()) {
            self.changeMessage(
                'You have already submitted. You cannot sign up more than once.',
                'text-danger p-xs'
            );
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
        window.ga('send', 'event', 'signupSubmit', 'click', 'new_user_submit');
        $osf.postJSON(
            submitUrl,
            ko.toJS(self)
        ).done(
            self.submitSuccess
        ).fail(
            self.submitError
        );
    },


});

/** Wrapper classes */
var ChangePassword = function(selector) {
    $osf.applyBindings(new ChangePasswordViewModel(), selector);
};

var SetPassword = function(selector) {
    $osf.applyBindings(new SetPasswordViewModel(), selector);
};

var SignUp = function(selector) {
    $osf.applyBindings(new SignUpViewModel(), selector);
};

module.exports = {
    ChangePassword: ChangePassword,
    SetPassword: SetPassword,
    SignUp: SignUp
};

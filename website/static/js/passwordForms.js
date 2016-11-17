'use strict';

var ko = require('knockout');
require('knockout.validation');
var $ = require('jquery');
var zxcvbn = require('zxcvbn');

var oop = require('js/oop');
var $osf = require('./osfHelpers');
var ChangeMessageMixin = require('js/changeMessage');
require('js/knockoutPassword');

ko.validation.init({
    insertMessages : false
});

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
    1: {'attr': {'class': 'progress-bar progress-bar-sm progress-bar-danger', 'style': 'width: 20%'}, 'text': 'Very weak', 'text_attr': {'class': 'text-danger'}},
    2: {'attr': {'class': 'progress-bar progress-bar-sm progress-bar-danger', 'style': 'width: 40%'}, 'text': 'Weak', 'text_attr': {'class': 'text-danger'}},
    3: {'attr': {'class': 'progress-bar progress-bar-sm progress-bar-warning', 'style': 'width: 60%'}, 'text': 'So-so', 'text_attr': {'class': 'text-warning'}},
    4: {'attr': {'class': 'progress-bar progress-bar-sm progress-bar-success', 'style': 'width: 80%;'}, 'text': 'Good', 'text_attr': {'class': 'text-success'}},
    5: {'attr': {'class': 'progress-bar progress-bar-sm progress-bar-success', 'style': 'width: 100%'}, 'text': 'Great!', 'text_attr': {'class': 'text-success'}}
};

/**
 * Base view model for other password-setting view-models. Stores password input
 * with password verification.
 */
var BaseViewModel = oop.extend(ChangeMessageMixin, {
    constructor: function () {
        var self = this;
        ChangeMessageMixin.call(self);
        self.typedPassword = ko.observable('').extend({passwordChecking: true});
        self.passwordFeedback = self.typedPassword.passwordFeedback;

        self.passwordComplexityInfo = ko.computed(function() {
            return valueProgressBar[self.typedPassword.passwordComplexity()];
        });

        self.password = ko.observable('').extend({
            required: true,
            minLength: 8,
            maxLength: 255,
            complexity: 2,
        });

        // To ensure that validated fields are populated correctly
        self.validatedObservables = self.getValidatedFields();
        self.validatedFields = ko.validatedObservable(self.validatedObservables);

        // Collect validated fields
        self.validatedFields = ko.validatedObservable(self.validatedObservables);

        self.submitted = ko.observable(false);
        self.trim = function(observable) {
            observable($.trim(observable()));
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
        var self = this;
        return {password: self.password};
    }
});


var ChangePasswordViewModel = oop.extend(BaseViewModel, {
    constructor: function () {
        var self = this;

        // Call constructor at the beginning so that self.password exists
        self.super.constructor.call(this);

        // pick up the email from contextVars
        self.email1 = ko.observable(window.contextVars.username || '').extend({
            required: true,
            email: true
        });

        self.oldPassword = ko.observable('').extend({required: true});

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
                'message': 'Your new password cannot be the same as your old password.',
                params: self.oldPassword
            }
        });

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

    },
    getValidatedFields: function() {
        var self = this;
        return {
            password: self.password,
            passwordConfirmation: self.passwordConfirmation,
            oldPassword: self.oldPassword
        };
    }
});


var SetPasswordViewModel = oop.extend(BaseViewModel, {
    constructor: function () {
        var self = this;
        // Call constructor at the beginning so that self.password exists
        self.super.constructor.call(this);

        // pick up the email from contextVars if we can't get it from first typing it in
        self.email1 = ko.observable(window.contextVars.username || '').extend({
            required: true,
            email: true
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
    constructor: function (submitUrl, campaign) {
        var self = this;
        self.campaign = campaign;
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

        // Call constructor after declaring observables so that validatedFields is populated correctly
        self.super.constructor.call(this, submitUrl);

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
            password: self.password,
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
        /* jshint ignore: start */
        if (typeof grecaptcha !== 'undefined') {
            grecaptcha.reset();
        }
        /* jshint ignore: end */
        self.changeMessage(
            xhr.responseJSON.message_long,
            'text-danger p-xs',
            5000
        );
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
            $.each(self.validatedObservables, function(key, value) {
                value.notifySubscribers();
            });
            return false;
        }

        var payload = ko.toJS(self);

        // include recaptcha if it is enabled
        if ($('.g-recaptcha').length !== 0) {
            var captchaResponse = $('#g-recaptcha-response').val();
            if (captchaResponse.length === 0) {
                return false;
            }
            $.extend(payload, {'g-recaptcha-response': captchaResponse});
        }

        window.ga('send', 'event', 'signupSubmit', 'click', 'new_user_submit');
        $osf.postJSON(
            submitUrl,
            payload
        ).done(
            self.submitSuccess.bind(self)
        ).fail(
            self.submitError.bind(self)
        );
    },


});

/** Wrapper classes */
var ChangePassword = function(selector) {
    var viewModel = new ChangePasswordViewModel();
    $osf.applyBindings(viewModel, selector);
    // Necessary to prevent enter submitting forms with invalid frontend zxcvbn validation
    $(selector).keypress(function(event) {
        if (event.which === 13) {
            if (!viewModel.password.isValid() || !viewModel.passwordConfirmation.isValid()) {
                return false;
            }
        }
    });
};

var SetPassword = function(selector) {
    var viewModel = new SetPasswordViewModel();
    $osf.applyBindings(viewModel, selector);
    // Necessary to prevent enter submitting forms with invalid frontend zxcvbn validation
    $(selector).keypress(function(event) {
        if (event.which === 13) {
            if (!viewModel.password.isValid() || !viewModel.passwordConfirmation.isValid()) {
                return false;
            }
        }
    });
};

var SignUp = function(selector, campaign) {
    var viewModel = new SignUpViewModel(undefined, campaign);
    $osf.applyBindings(viewModel, selector);
    // Necessary to prevent enter submitting forms with invalid frontend zxcvbn validation
    $(selector).keypress(function(event) {
        if (event.which === 13) {
            if (!viewModel.password.isValid()) {
                return false;
            }
        }
    });
};

module.exports = {
    ChangePassword: ChangePassword,
    SetPassword: SetPassword,
    SignUp: SignUp
};

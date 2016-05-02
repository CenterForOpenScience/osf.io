'use strict';

var ko = require('knockout');
require('knockout.validation');
var $ = require('jquery');

var $osf = require('./osfHelpers');
var zxcvbn = require('zxcvbn');


var ViewModel = function() {

    var self = this;

    self.typedPassword = ko.observable('');

    self.passwordFeedback = ko.observable('');

    self.passwordComplexity = ko.pureComputed(function() {
        var current = zxcvbn(self.typedPassword());
        self.passwordFeedback(current.feedback.warning);
        return current.score;
    });

    self.passwordComplexityBar = ko.computed(function() {
        if (self.passwordComplexity() === 0) {
            return {
                class: 'progress-bar progress-bar-danger',
                style: 'width: 0%'
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
    });

    self.password = ko.observable('').extend({
        required: true,
        minLength: 6,
        maxLength: 256,
        complexity: 2
    });

    self.password_confirmation = ko.observable('').extend({
        required: true,
        validation: {
            validator: function(val, other) {
                return String(val).toLowerCase() === String(other).toLowerCase();
            },
            'message': 'Passwords must match.',
            params: self.password
        }
    });

    // Preserve object of validated fields for use in `submit`
    var validatedFields = {
        password: self.password,
        password_confirmation: self.password_confirmation
    };
    // Collect validated fields
    self.validatedFields = ko.validatedObservable($.extend({}, validatedFields));

    self.trim = function(observable) {
        observable($.trim(observable()));
    };

    self.isValid = ko.computed(function() {
        return self.validatedFields.isValid();
    });

    self.submit = function() {
        // Show errors if invalid
        if (!self.isValid()) {
            // Ensure validation errors are displayed
            $.each(validatedFields, function(key, value) {
                value.notifySubscribers();
            });
            return false;
        }
        // Else submit
        $osf.postJSON(
            '',
            ko.toJS(self)
        );
    };

    self.errors = ko.validation.group(self);

};

var ResetPassword = function(selector) {
    this.viewModel = new ViewModel();
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = ResetPassword;

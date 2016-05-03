'use strict';

var ko = require('knockout');
require('knockout.validation');
var $ = require('jquery');

var $osf = require('./osfHelpers');
var zxcvbn = require('zxcvbn');


var ViewModel = function() {

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

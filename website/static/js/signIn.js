/**
 * Sign in view model used for login components
 */
'use strict';

var ko = require('knockout');
require('knockout-validation').init({insertMessages: false});  // override default DOM insertions

var $osf = require('osfHelpers');
var $formViewModel = require('formViewModel');


var SignInViewModel = function() {
    // Call constructor for superclass
    $formViewModel.FormViewModel.call(this);

    var self = this;

    self.username = ko.observable('').extend({
        required: true,
        email: true
    });
    self.password = ko.observable('').extend({
        required: true,
        minLength: 6,
        maxLength: 35
    });
};

SignInViewModel.prototype = Object.create($formViewModel.FormViewModel.prototype);
// Set the "constructor property" to refer to FormViewModel
SignInViewModel.prototype.constructor = $formViewModel.FormViewModel;

// Subclass methods for ForgotPasswordViewModel
SignInViewModel.prototype.isValid = function() {
    var validationErrors = [];
    if (!this.username.isValid()) {
        validationErrors.push(
            new $formViewModel.ValidationError(
                'Error',
                'Please enter a valid email address.'
            )
        );
    }
    if (!this.password.isValid()) {
        validationErrors.push(
            new $formViewModel.ValidationError(
                'Error',
                'Your password must be more than six but fewer than 36 characters.'
            )
        );
    }
    if (validationErrors.length > 0) {
        throw validationErrors;
    } else {
        return true;
    }
};

var SignIn = function(selector, applyBindings) {
    this.viewModel = new SignInViewModel();
    if (applyBindings === true) {
        $osf.applyBindings(this.viewModel, selector);
    }
};

module.exports = {
    SignIn: SignIn,
    ViewModel: SignInViewModel
};

/*
 * forgot password view model
 */
'use strict';

var ko = require('knockout');
require('knockout-validation');

var $osf = require('js/osfHelpers');
var formViewModel = require('js/formViewModel');


var ForgotPasswordViewModel = function() {
    // Call constructor for superclass
    formViewModel.FormViewModel.call(this);

    var self = this;
    self.username = ko.observable('').extend({
        required: true,
        email: true
    });
};

ForgotPasswordViewModel.prototype = Object.create(formViewModel.FormViewModel.prototype);
// Set the "constructor property" to refer to FormViewModel
ForgotPasswordViewModel.prototype.constructor = formViewModel.FormViewModel;

// Subclass methods for ForgotPasswordViewModel
ForgotPasswordViewModel.prototype.isValid = function() {
    if (!this.username.isValid()) {
        var validationErrors = [
            new formViewModel.ValidationError(
                'Error',
                'Please enter a valid email address.'
            )
        ];
        throw validationErrors;
    } else {
        return true;
    }
};


var ForgotPassword = function(selector, applyBindings) {
    this.viewModel = new ForgotPasswordViewModel();
    if (applyBindings) {  // Apply bindings if viewmodel is not a child component
        $osf.applyBindings(this.viewModel, selector);
    }
};

module.exports = {
    ForgotPassword: ForgotPassword,
    ViewModel: ForgotPasswordViewModel
};

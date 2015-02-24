/*
 * forgot password view model
 */
'use srict';

var ko = require('knockout');
require('knockout-validation');
var $ = require('jquery');

var $osf = require('osfHelpers');

var ViewModel = function() {

    var self = this;

    self.username = ko.observable('').extend({
        required: true,
        email: true
    });

    self.isValid = ko.computed(function() {
        return self.username.isValid();
    });

    self.submit = function() {
        // Show errors if invalid
        if (!self.isValid()) {
            $osf.growl(
                'Error',
                'Please enter a correctly formatted email address.',
                'warning'
            );
            $('[name="forgot_password-email"]').focus();
            return false; // Stop form submission
        }
        return true; // Allow form to submit normally
    }
};


var ForgotPassword = function(selector, applyBindings) {
    this.viewModel = new ViewModel();
    if (applyBindings) {  // Apply bindings if viewmodel is not a child component
        $osf.applyBindings(this.viewModel, selector);
    }
};

module.exports = ForgotPassword;  // webpack export
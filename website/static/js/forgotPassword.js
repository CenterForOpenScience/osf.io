/*
 * forgot password view model
 */
'use srict';

var ko = require('knockout');
require('knockout-validation');

var $osf = require('osfHelpers');

var ViewModel = function() {

    var self = this;

    self.username = ko.observable('').extend({
        required: true,
        email: true
    });

    self.submit = function() {
        // Show errors if invalid
        if (!self.username.isValid()) {
            $osf.growl(
                'Error',
                'Please enter a correctly formatted email address.',
                'warning'
            );
            return false; // Stop form submission
        }
        return true; // Allow form to submit normally
    };
};


var ForgotPassword = function(selector) {
    this.viewModel = new ViewModel();
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    ForgotPassword: ForgotPassword,
    ViewModel: ViewModel
};

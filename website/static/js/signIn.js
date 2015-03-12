/**
 * Sign in view model used for login components
 */
'use strict';

var ko = require('knockout');
require('knockout-validation').init({insertMessages: false});  // override default DOM insertions
var $ = require('jquery');

var $osf = require('js/osfHelpers');

var ViewModel = function() {

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

    self.isValid = ko.pureComputed(function() {
        return self.username.isValid() && self.password.isValid();
    });

    self.submit = function() {
        // Show errors if invalid
        if (!self.isValid()) {
            if (!self.username.isValid()) {
                $osf.growl(
                    'Error',
                    'Please enter a valid email address.',
                    'danger'
                );
            }
            if (!self.password.isValid()) {
                $osf.growl(
                    'Error',
                    'Your password must be more than six characters.',
                    'danger'
                );
            }
            return false; // Stop form submission
        } else {
            return true;  // Allow form to submit normally
        }
    };
};


var SignIn = function(selector) {
    this.viewModel = new ViewModel();
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    SignIn: SignIn,
    ViewModel: ViewModel
};

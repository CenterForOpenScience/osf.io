/**
 * Sign in view model used for login components
 */
'use strict';

var ko = require('knockout');
require('knockout.validation').init({insertMessages: false});  // override default DOM insertions

var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var formViewModel = require('js/formViewModel');


var SignInViewModel = oop.extend(formViewModel.FormViewModel, {
    constructor: function () {
        var self = this;
        self.super.constructor.call(self);
        var existingUserEmail = decodeURIComponent($osf.urlParams().existing_user);

        if (existingUserEmail.existing_user) {
            self.username = ko.observable(existingUserEmail.existing_user).extend({
                required: true,
                email: true
            });
        }
        else {
            self.username = ko.observable('').extend({
                required: true,
                email: true
            });
        }
        // Allow server to validate password
        self.password = ko.observable('');
    },
    isValid: function() {
        var validationError = new formViewModel.ValidationError();
        if (!this.username.isValid()) {
            validationError.messages.push('Please enter a valid email address.');
        }
        if (validationError.messages.length > 0) {
            throw validationError;
        }
    }
});


var SignIn = function(selector) {
    this.viewModel = new SignInViewModel();
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    SignIn: SignIn,
    ViewModel: SignInViewModel
};

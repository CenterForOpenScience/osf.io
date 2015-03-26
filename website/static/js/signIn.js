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
        self.username = ko.observable('').extend({
            required: true,
            email: true
        });
        self.password = ko.observable('').extend({
            required: true,
            minLength: 6,
            maxLength: 35
        });
    },
    isValid: function() {
        var validationError = new formViewModel.ValidationError();
        if (!this.username.isValid()) {
            validationError.messages.push('Please enter a valid email address.');
        }
        if (!this.password.isValid()) {
            validationError.messages.push('Your password must be more than six but fewer than 36 characters.');
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

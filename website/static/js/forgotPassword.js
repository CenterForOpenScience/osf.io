/*
 * forgot password view model
 */
'use strict';

var ko = require('knockout');
require('knockout-validation');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var formViewModel = require('js/formViewModel');


var ForgotPasswordViewModel = oop.extend(formViewModel.FormViewModel, {
    constructor: function() {
        var self = this;
        self.super.constructor();
        self.username = ko.observable('').extend({
            required: true,
            email: true
        });
    },
    isValid: function() {
        var ValidationError = new formViewModel.ValidationError();
        if (!this.username.isValid()) {
            ValidationError.messages.push('Please enter a valid email address.');
            throw ValidationError;
        } else {
            return true;
        }
    }
});

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
        throw new formViewModel.ValidationError(['Please enter a valid email address.']);
    } else {
        return true;
    }
};


var ForgotPassword = function(selector) {
    this.viewModel = new ForgotPasswordViewModel();
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    ForgotPassword: ForgotPassword,
    ViewModel: ForgotPasswordViewModel
};

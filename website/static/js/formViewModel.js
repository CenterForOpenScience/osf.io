/*
 * Maintains the base class for knockoutJS form ViewModels
 */
'use strict';

var ko = require('knockout');

var $osf = require('osfHelpers');


var ValidationError = function(errorHeader, errorMessage) {
    this.errorHeader = errorHeader;
    this.errorMessage = errorMessage;
    this.errorLevel = 'warning';
};

var FormViewModel = function() {

    // Abstract method each ViewModel must impliment. Expected behavior is to either return true
    // or an array of ValidationError objects
    self.isValid = function() {
        throw "Not Implemented";
    };

    self.submit = function() {
        try {
            this.isValid();
            return true; // Allow form to submit normally
        } catch (ValidationErrors) {
            for (var i = 0; i < ValidationErrors.length; i++) {
                $osf.growl(
                    ValidationErrors[i].errorHeader,
                    ValidationErrors[i].errorMessage,
                    ValidationErrors[i].errorLevel
                );
            }
            return false; // Stop form submission
        }
    };
};

module.exports = {
    FormViewModel: FormViewModel,
    ValidationError: ValidationError
};
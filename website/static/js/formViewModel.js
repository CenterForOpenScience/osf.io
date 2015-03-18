/*
 * Maintains the base class for knockoutJS form ViewModels
 */
'use strict';

var ko = require('knockout');

var $osf = require('osfHelpers');
var oop = require('js/oop');

var ValidationError = oop.extend(Error, {
    constructor: function (messages, header, level) {
        this.super.constructor();
        this.messages = messages || [];
        this.header = header || 'Error';
        this.level = level || 'warning';
    }
});

var FormViewModel = oop.defclass({
    constructor: function() {
        var self = this;
    },
    isValid: function() {
        throw new Error('FormViewModel subclass must implement isValid');
    },
    submit: function() {
        try {
            this.isValid();
            return true; // Allow form to submit normally
        } catch (ValidationError) {
            for (var i = 0; i < ValidationError.messages.length; i++) {
                $osf.growl(
                    ValidationError.header,
                    ValidationError.messages[i],
                    ValidationError.level
                );
            }
            return false; // Stop form submission
        }
    }
});


module.exports = {
    FormViewModel: FormViewModel,
    ValidationError: ValidationError
};
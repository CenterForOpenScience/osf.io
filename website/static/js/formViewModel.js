/*
 * Maintains the base class for knockoutJS form ViewModels
 */
'use strict';


var $osf = require('js/osfHelpers');
var oop = require('js/oop');

var ValidationError = oop.extend(Error, {
    constructor: function (messages, header, level) {
        this.super.constructor.call(this);
        this.messages = messages || [];
        this.header = header || 'Error';
        this.level = level || 'warning';
    }
});

/**
* Base class KO viewmodel based forms should inherit from.
*
* Note: isValid needs to be implemented by subclasses and onError can
* optionally be implemented by subclasses to handle ValidationError(s) as desired.
*/
var FormViewModel = oop.defclass({
    constructor: function() {},
    isValid: function() {
        throw new Error('FormViewModel subclass must implement isValid');
    },
    onError: function(validationError) {
        for (var i = 0; i < validationError.messages.length; i++) {
            $osf.growl(
                validationError.header,
                validationError.messages[i],
                validationError.level
            );
        }
    },
    submit: function() {
        try {
            this.isValid();
            return true; // Allow form to submit normally
        } catch (err) {
            if (err instanceof ValidationError) {
                this.onError(err);
                return false; // Stop form submission
            } else {
                throw err;
            }
        }
    }
});


module.exports = {
    FormViewModel: FormViewModel,
    ValidationError: ValidationError
};
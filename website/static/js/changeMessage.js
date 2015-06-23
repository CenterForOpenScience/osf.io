/**
 * ViewModel mixin for displaying form input help messages.
 * Adds message and messageClass observables that can be changed with the
 * changeMessage method.
 */
'use strict';
var ko = require('knockout');
var oop = require('js/oop');
/** Change the flashed status message */

var ChangeMessageMixin = oop.defclass({
    constructor: function() {
        this.message = ko.observable('');
        this.messageClass = ko.observable('text-info');
    },
    changeMessage: function(text, css, timeout) {
        var self = this;
        if (typeof text === 'function') {
            text = text();
        }
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            window.setTimeout(function () {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    },
    resetMessage: function() {
        this.message('');
        this.messageClass('text-info');
    }
});

module.exports = ChangeMessageMixin;

webpackJsonp([40],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

/**
 * registration retraction ES
**/

var RegistrationRetraction = __webpack_require__(414);

var submitUrl = window.contextVars.node.urls.api + 'retraction/';

var registrationTitle = window.contextVars.node.title;

new RegistrationRetraction.RegistrationRetraction('#registrationRetraction', submitUrl, registrationTitle);


/***/ },

/***/ 379:
/***/ function(module, exports, __webpack_require__) {

/**
 * ViewModel mixin for displaying form input help messages.
 * Adds message and messageClass observables that can be changed with the
 * changeMessage method.
 */
'use strict';
var ko = __webpack_require__(48);
var oop = __webpack_require__(146);
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


/***/ },

/***/ 414:
/***/ function(module, exports, __webpack_require__) {

/**
 * On page load, maintains knockout ViewModel
**/
'use strict';

var $ = __webpack_require__(38);
var $osf = __webpack_require__(47);

var ko = __webpack_require__(48);
var koHelpers = __webpack_require__(142);
__webpack_require__(143);

var ChangeMessageMixin = __webpack_require__(379);
var oop = __webpack_require__(146);
var Raven = __webpack_require__(52);


var RegistrationRetractionViewModel = oop.extend(
    ChangeMessageMixin,
    {
        constructor: function(submitUrl, registrationTitle) {
            this.super.constructor.call(this);

            var self = this;

            self.submitUrl = submitUrl;
            self.registrationTitle = $osf.htmlDecode(registrationTitle);
            // Truncate title to around 50 chars
            var parts = self.registrationTitle.slice(0, 50).split(' ');
            if (parts.length > 1) {
                self.truncatedTitle = parts.slice(0, -1).join(' ');
            }
            else {
                self.truncatedTitle = parts[0];
            }

            self.justification = ko.observable('').extend({
                maxLength: 2048
            });
            self.confirmationText = ko.observable().extend({
                required: true,
                mustEqual: self.truncatedTitle
            });
            self.disableSave = ko.observable(false);
            self.valid = ko.computed(function(){
                return !self.disableSave() && self.confirmationText.isValid();
            });
        },
        SUBMIT_ERROR_MESSAGE: 'Error submitting your retraction request, please try again. If the problem ' +
                'persists, email <a href="mailto:support@osf.iop">support@osf.io</a>',
        CONFIRMATION_ERROR_MESSAGE: 'Please enter the registration title before clicking Retract Registration',
        JUSTIFICATON_ERROR_MESSAGE: 'Your justification is too long, please enter a justification with no more ' +
            'than 2048 characters long.',
        MESSAGE_ERROR_CLASS: 'text-danger',
        onSubmitSuccess: function(response) {            
            window.location = response.redirectUrl;
        },
        onSubmitError: function(xhr, status, errorThrown) {
            var self = this;
            self.disableSave(false);
            self.changeMessage(self.SUBMIT_ERROR_MESSAGE, self.MESSAGE_ERROR_CLASS);
            Raven.captureMessage('Could not submit registration retraction.', {
                xhr: xhr,
                status: status,
                error: errorThrown
            });
        },
        submit: function() {
            var self = this;
            self.disableSave(true);
            // Show errors if invalid
            if (!self.confirmationText.isValid()) {
                self.changeMessage(self.CONFIRMATION_ERROR_MESSAGE, self.MESSAGE_ERROR_CLASS);
                return false;
            } else if (!self.justification.isValid()) {
                self.changeMessage(self.JUSTIFICATON_ERROR_MESSAGE, self.MESSAGE_ERROR_CLASS);
                return false;
            } else {
                // Else Submit
                return $osf.postJSON(self.submitUrl, ko.toJS(self))
                    .done(self.onSubmitSuccess.bind(self))
                    .fail(self.onSubmitError.bind(self));
            }
        }
});

var RegistrationRetraction = function(selector, submitUrl, registrationTitle) {
    this.viewModel = new RegistrationRetractionViewModel(submitUrl, registrationTitle);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    RegistrationRetraction: RegistrationRetraction,
    ViewModel: RegistrationRetractionViewModel
};


/***/ }

});
//# sourceMappingURL=registration-retraction-page.js.map
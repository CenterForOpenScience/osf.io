var ko = require('knockout');
var moment = require('moment');
require('pikaday');
require('pikaday-css');
var bootbox = require('bootbox');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var language = require('js/osfLanguage').registrations;

var template = require('raw!templates/registration-modal.html');
$(document).ready(function() {
    $('body').append(template);
});

var MAKE_PUBLIC = {
    value: 'immediate',
    message: 'Make registration public immediately'
};
var MAKE_EMBARGO = {
    value: 'embargo',
    message: 'Enter registration into embargo'
};

var RegistrationViewModel = function(confirm, prompts, validator) {

    var self = this;


    // Wire up the registration options.

    self.registrationOptions = [
        MAKE_PUBLIC,
        MAKE_EMBARGO
    ];
    self.registrationChoice = ko.observable(MAKE_PUBLIC.value);


    // Wire up the embargo option.

    self.requestingEmbargo = ko.computed(function() {
        var choice = self.registrationChoice();
        return choice === MAKE_EMBARGO.value;
    });
    self.requestingEmbargo.subscribe(function(requestingEmbargo) {
        self.showEmbargoDatePicker(requestingEmbargo);
    });
    self.showEmbargoDatePicker = ko.observable(false);
    self.pikaday = ko.observable(new Date());  // interacts with a datePicker from koHelpers.js


    // Wire up embargo validation.
    // ---------------------------
    // All registrations undergo an approval process before they're made public
    // (though details differ based on the type of registration). We try to
    // require (for some reason) that the embargo lasts at least as long as the
    // approval period. On the other hand, we don't want (for some reason)
    // embargos to be *too* long.

    self.embargoEndDate = ko.computed(function() {
        return moment(new Date(self.pikaday()));
    });

    self._now = function() { return moment(); };  // this is a hook for testing

    self.embargoIsLongEnough = function(end) {
        var min = self._now().add(2, 'days');
        return end.isAfter(min);
    };

    self.embargoIsShortEnough = function(end) {
        var max = self._now().add(4, 'years').subtract(1, 'days');
        return end.isBefore(max);
    };

    var validation = [{
        validator: self.embargoIsLongEnough,
        message: 'Embargo end date must be at least three days in the future.'
    }, {
        validator: self.embargoIsShortEnough,
        message: 'Embargo end date must be less than four years in the future.'
    }];
    if(validator) {
        validation.unshift(validator);
    }
    self.embargoEndDate.extend({
        validation: validation
    });


    // Wire up the modal actions.

    self.canRegister = ko.pureComputed(function() {
        if (self.requestingEmbargo()) {
            return self.embargoEndDate.isValid();
        }
        return true;
    });

    self.confirm = confirm;
    self.preRegisterPrompts = prompts;
    self.close = bootbox.hideAll;
};
RegistrationViewModel.prototype.show = function() {
    var self = this;
    bootbox.dialog({
        size: 'large',
        title: language.registerConfirm,
        message: function() {
            ko.renderTemplate('registrationChoiceModal', self, {}, this);
        }
    });
};
RegistrationViewModel.prototype.register = function() {
    var end = this.embargoEndDate();
    this.confirm({
        registrationChoice: this.registrationChoice(),
        embargoEndDate: end,
        embargoIsLongEnough: this.embargoIsLongEnough(end),
        embargoIsShortEnough: this.embargoIsShortEnough(end)
    });
};

module.exports = {
    ViewModel: RegistrationViewModel
};

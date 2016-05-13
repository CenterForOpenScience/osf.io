var ko = require('knockout');
var pikaday = require('pikaday');
require('pikaday-css');
var bootbox = require('bootbox');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var language = require('js/osfLanguage').registrations;

var template = require('raw!templates/registration-modal.html');
$(document).ready(function() {
    $('body').append(template);
});

// TODO(hrybacki): Import min/max dates from website.settings
var TWO_DAYS_FROM_TODAY_TIMESTAMP = new Date().getTime() + (2 * 24 * 60 * 60 * 1000);
var FOUR_YEARS_FROM_TODAY_TIMESTAMP = new Date().getTime() + (1460 * 24 * 60 * 60 * 1000);

var MAKE_PUBLIC = {
    value: 'immediate',
    message: 'Make registration public immediately'
};
var MAKE_EMBARGO = {
    value: 'embargo',
    message: 'Enter registration into embargo'
};
var today = new Date();

var RegistrationViewModel = function(confirm, prompts, validator) {

    var self = this;

    self.registrationOptions = [
        MAKE_PUBLIC,
        MAKE_EMBARGO
    ];
    self.registrationChoice = ko.observable(MAKE_PUBLIC.value);

    self.pikaday = ko.observable(today);
    var picker = new pikaday(
        {
            bound: true,
            field: document.getElementById('endDatePicker'),
            onSelect: function() {
                self.pikaday(picker.toString());
                self.isEmbargoEndDateValid();
            }
        }
    );
    self.embargoEndDate = ko.computed(function() {
        return new Date(self.pikaday());
    });

    var validation = [{
        validator: function() {
            var endEmbargoDateTimestamp = self.embargoEndDate().getTime();
            return (endEmbargoDateTimestamp > TWO_DAYS_FROM_TODAY_TIMESTAMP);
        },
        message: 'Embargo end date must be at least three days in the future.'}, 
        {
        validator: function() {
            var endEmbargoDateTimestamp = self.embargoEndDate().getTime();
            return (endEmbargoDateTimestamp < FOUR_YEARS_FROM_TODAY_TIMESTAMP);
        },
        message: 'Embargo end date must be less than four years in the future.', 
    }];
    
    if(validator) {
        validation.unshift(validator);
    }
    self.pikaday.extend({
        validation: validation
    });

    self.showEmbargoDatePicker = ko.observable(false);
    self.requestingEmbargo = ko.computed(function() {
        var choice = self.registrationChoice();
        return choice === MAKE_EMBARGO.value;
    });
    self.requestingEmbargo.subscribe(function(requestingEmbargo) {
        self.showEmbargoDatePicker(requestingEmbargo);
    });

    self.canRegister = ko.pureComputed(function() {
        if (self.requestingEmbargo()) {
            return self.pikaday.isValid();
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
    this.confirm({
        registrationChoice: this.registrationChoice(),
        embargoEndDate: this.embargoEndDate()
    });
};

module.exports = {
    ViewModel: RegistrationViewModel
};

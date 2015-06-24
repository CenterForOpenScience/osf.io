var ko = require('knockout');
var pikaday = require('pikaday');

var RegistrationEmbargoViewModel = function() {

    var self = this;
    var MAKE_PUBLIC = {
        value: 'immediate',
        message: 'Make registration public immediately'
    };
    var MAKE_EMBARGO = {
        value: 'embargo',
        message: 'Enter registration into embargo'
    };
    var today = new Date();
    // TODO(hrybacki): Import min/max dates from website.settings
    var TWO_DAYS_FROM_TODAY_TIMESTAMP = new Date().getTime() + (2 * 24 * 60 * 60 * 1000);
    var FOUR_YEARS_FROM_TODAY_TIMESTAMP = new Date().getTime() + (1460 * 24 * 60 * 60 * 1000);

    self.registrationOptions = [
        MAKE_PUBLIC,
        MAKE_EMBARGO
    ];
    self.registrationChoice = ko.observable(MAKE_PUBLIC.value);

    self.pikaday = ko.observable(today);
    var picker = new pikaday(
        {
            field: document.getElementById('endDatePicker'),
            onSelect: function() {
                self.pikaday(picker.toString());
                self.isEmbargoEndDateValid();
            }
        }
    );
    self.showEmbargoDatePicker = ko.observable(false);
    self.checkShowEmbargoDatePicker = function() {
        self.showEmbargoDatePicker(self.registrationChoice() === MAKE_EMBARGO.value);
    };
    self.embargoEndDate = ko.computed(function() {
        return new Date(self.pikaday());
    });
    self.isEmbargoEndDateValid = ko.computed(function() {
        var endEmbargoDateTimestamp = self.embargoEndDate().getTime();
        return (endEmbargoDateTimestamp < FOUR_YEARS_FROM_TODAY_TIMESTAMP && endEmbargoDateTimestamp > TWO_DAYS_FROM_TODAY_TIMESTAMP);
    });
    self.requestingEmbargo = ko.pureComputed(function() {
        var choice = self.registrationChoice();
        if (choice) { return choice === MAKE_EMBARGO.value; }
    });
};

var RegistrationEmbargo = function(selector) {
    this.viewModel = new RegistrationEmbargoViewModel();
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    RegistrationEmbargo: RegistrationEmbargo,
    ViewModel: RegistrationEmbargoViewModel
};
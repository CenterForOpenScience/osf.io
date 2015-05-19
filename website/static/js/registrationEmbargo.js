var ko = require('knockout');
var pikaday = require('pikaday');

var RegistrationEmbargoViewModel = function() {

    var self = this;
    var MAKE_PUBLIC = 'Make registration public immediately';
    var MAKE_EMBARGO = 'Enter registration into embargo';
    var today = new Date();
    var TWO_DAYS_FROM_TODAY_TIMESTAMP = new Date().getTime() + (2 * 24 * 60 * 60 * 1000);
    var ONE_YEAR_FROM_TODAY_TIMESTAMP = new Date().getTime() + (365 * 24 * 60 * 60 * 1000);

    self.registrationOptions = ko.observableArray([
        MAKE_PUBLIC,
        MAKE_EMBARGO
    ]);
    self.registrationChoice = ko.observable(MAKE_PUBLIC);

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
        if (self.registrationChoice()[0] === MAKE_EMBARGO) {
            self.showEmbargoDatePicker(true);
        } else {
            self.showEmbargoDatePicker(false);
        }
    };
    self.embargoEndDate = ko.computed(function() {
        return new Date(self.pikaday());
    });
    self.isEmbargoEndDateValid = ko.computed(function() {
        var endEmbargoDateTimestamp = self.embargoEndDate().getTime();
        if (endEmbargoDateTimestamp < ONE_YEAR_FROM_TODAY_TIMESTAMP && endEmbargoDateTimestamp > TWO_DAYS_FROM_TODAY_TIMESTAMP) {
            return true;
        } else { return false; }
    });
    self.requestingEmbargo = ko.computed(function() {
        var choice = self.registrationChoice();
        if (choice) { return choice[0] === MAKE_EMBARGO; }
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
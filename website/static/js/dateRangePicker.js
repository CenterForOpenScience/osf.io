/**
 * Date range picker.
 */

'use strict';

require('pikaday-css');

var oop = require('js/oop');
var pikaday = require('pikaday');


var DateRangePicker = oop.defclass({
    constructor: function(startPickerElem, startDate, endPickerElem, endDate, minDate, maxDate) {
        var self = this;

        self.minDate = minDate;
        self.maxDate = maxDate;

        self.startDate = startDate;
        self.startPickerElem = startPickerElem;
        self._startPicker = self._makePicker(startPickerElem, 'startDate', 'updateStartDate');

        self.endDate = endDate;
        self.endPickerElem = endPickerElem;
        self._endPicker = self._makePicker(endPickerElem, 'endDate', 'updateEndDate');

        self.updateStartDate(self.startDate);
        self.updateEndDate(self.endDate);
    },
    _makePicker: function(pickerElem, dateProp, updateDateFunc) {
        var self = this;
        return new pikaday({
            bound: true,
            field: pickerElem,
            defaultDate: self[dateProp],
            setDefaultDate: true,
            minDate: self.minDate,
            maxDate: self.maxDate,
            onSelect: function() {
                self[dateProp] = this.getDate();
                self[updateDateFunc](self[dateProp]);
                pickerElem.value = this.toString();
            }
        });
    },
    updateStartDate: function(start) {
        var self = this;
        self._startPicker.setStartRange(start);
        self._endPicker.setStartRange(start);
        self._endPicker.setMinDate(start);
    },
    updateEndDate: function(end) {
        var self = this;
        self._startPicker.setEndRange(end);
        self._startPicker.setMaxDate(end);
        self._endPicker.setEndRange(end);
    },
});


module.exports = DateRangePicker;

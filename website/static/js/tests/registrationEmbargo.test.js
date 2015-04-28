/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var registrationEmbargo = require('js/registrationEmbargo');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('registrationEmbargo', () => {

    describe('RegistrationEmbargoViewModel', () => {
        var vm;
        var MAKE_PUBLIC = 'Make registration public immediately';
        var MAKE_EMBARGO = 'Enter registration into embargo';

        beforeEach(() => {
            vm = new registrationEmbargo.ViewModel();
        });

        describe('#dayOptions', () => {
            it('returns array of 31 days for relevant months', () => {
                vm.monthChoice('January');
                var expectedDayOptions = [];
                for (var i=1; i<=31; i+=1) { expectedDayOptions.push(i); }
                assert.equal(
                    JSON.stringify(vm.dayOptions()),
                    JSON.stringify(expectedDayOptions)
                );
            });
            it('returns array of 30 days for relevant months', () => {
                vm.monthChoice('June');
                var expectedDayOptions = [];
                for (var i=1; i<=30; i+=1) { expectedDayOptions.push(i); }
                assert.equal(
                    JSON.stringify(vm.dayOptions()),
                    JSON.stringify(expectedDayOptions)
                );
            });
            it('returns array of 28 days for February', () => {
                vm.monthChoice('February');
                var expectedDayOptions = [];
                for (var i=1; i<=28; i+=1) { expectedDayOptions.push(i); }
                assert.equal(
                    JSON.stringify(vm.dayOptions()),
                    JSON.stringify(expectedDayOptions)
                );
            });
        });
        describe('#yearOptions', () => {
            it('returns list of current year and next', () => {
                var currentYear = new Date().getFullYear();
                assert.equal(
                    JSON.stringify(vm.yearOptions()),
                    JSON.stringify([currentYear, currentYear+1])
                );
            });
        });
        describe('#checkShowEmbargoDatePicker', () => {
            it('returns false if registrationChoice is make public', () => {
                vm.registrationChoice([MAKE_PUBLIC]);
                vm.checkShowEmbargoDatePicker();
                assert.isFalse(vm.showEmbargoDatePicker());
            });
            it('returns true if registrationChoice is make embargo', () => {
                vm.registrationChoice([MAKE_EMBARGO]);
                vm.checkShowEmbargoDatePicker();
                assert.isTrue(vm.showEmbargoDatePicker());
            });
        });
        describe('#embargoEndDate', () => {
            it('returns Date from user input', () =>{
                vm.dayChoice(1);
                vm.monthChoice('March');
                vm.yearChoice(2015);

                var date = vm.embargoEndDate();
                assert.isTrue(date instanceof Date);
            });
            it('returns Invalid Date if no user input provided', () => {
                var date = vm.embargoEndDate();
                assert.equal(date, 'Invalid Date');
            });
        });
        describe('#isEmbargoEndDateValid', () => {
            it('returns true for date more than 2 days but less than 365 days in the future', () => {
                var today = new Date();
                vm.yearChoice(today.getYear() + 1900);  // years begin at 1900
                vm.monthChoice(vm.monthOptions()[today.getMonth()]);
                vm.dayChoice(today.getDate() + 3);

                assert.isTrue(vm.isEmbargoEndDateValid());
            });
            it('returns false for date less than 2 days in the future', () => {
                var today = new Date();
                vm.yearChoice(today.getYear() + 1900);  // years begin at 1900
                vm.monthChoice(vm.monthOptions()[today.getMonth()]);
                vm.dayChoice(today.getDate() + 2);

                assert.isFalse(vm.isEmbargoEndDateValid());
            });
            it('returns false for date more than 365 days in the future', () => {
                var today = new Date();
                vm.yearChoice(today.getYear() + 1901);  // years begin at 1900
                vm.monthChoice(vm.monthOptions()[today.getMonth()]);
                vm.dayChoice(today.getDate() + 2);

                assert.isFalse(vm.isEmbargoEndDateValid());
            });
        });
        describe('#requestingEmbargo', () => {
            it('returns false if user chose make public', () => {
                vm.registrationChoice([MAKE_PUBLIC]);
                assert.isFalse(vm.requestingEmbargo());
            });
            it('returns true if user chose requests embargo', () => {
                vm.registrationChoice([MAKE_EMBARGO]);
                assert.isTrue(vm.requestingEmbargo());
            });
        });
    });
});


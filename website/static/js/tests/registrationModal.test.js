/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var utils = require('tests/utils');
var faker = require('faker');

var RegistrationModal = require('js/registrationModal').ViewModel;

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {
    prefix: ''
});

describe('registrationModal', () => {
    sinon.collection.restore();
    var MAKE_PUBLIC = 'immediate';
    var MAKE_EMBARGO = 'embargo';

    var confirm = sinon.stub();
    var vm = new RegistrationModal(
        confirm, 
        [],
        null
    ); 
    beforeEach(() => {
        vm = new RegistrationModal(
            confirm, 
            [],
            null
        );
    });
    afterEach(() => {
        confirm.reset();
    });

    describe('#constructor', () => {
        it('takes a confirm method as a callback for bootbox success', () => {
            var args = {
                registrationChoice: vm.registrationChoice(),
                embargoEndDate: vm.embargoEndDate()
            };
            vm.register();
            assert.isTrue(confirm.calledWith(args));
        });
        it('takes an optional knockout validator', () => {
            var validate = sinon.spy();
            var instance = new RegistrationModal(
                function() {},
                [],
                {
                    validator: validate,
                    message: 'Bad, bad, bad.'
                }
            );
            var d = new Date();
            d.setDate(d.getDate() + 3);
            instance.pikaday(d);
            instance.pikaday.isValid();
            assert.isTrue(validate.called);
        });
    });
    describe('#embargoEndDate', () => {
        it('returns Date from user input', () => {
            vm.pikaday('2015-01-01');
            var date = vm.embargoEndDate();
            assert.isTrue(date instanceof Date);
        });
    });
    describe('#requestingEmbargo', () => {
        it('is true if the current registrationChoice is embargo', () => {
            vm.registrationChoice(MAKE_EMBARGO);
            assert.isTrue(vm.requestingEmbargo());
            vm.registrationChoice(MAKE_PUBLIC);
            assert.isFalse(vm.requestingEmbargo());
        });
    });
    describe('#pikaday.isValid', () => {             
        it('returns true for date more than 2 days but less than 4 years in the future', () => {
            var validDate = new Date();
            validDate.setDate(validDate.getDate() + 3);
            vm.pikaday(validDate);
            assert.isTrue(vm.pikaday.isValid());
        });
        it('returns false for date less than 2 days in the future', () => {
            var invalidPastDate = new Date();
            invalidPastDate.setDate(invalidPastDate.getDate() - 2);
            vm.pikaday(invalidPastDate);
            assert.isFalse(vm.pikaday.isValid());
        });
        it('returns false for date more than 4 years in the future', () => {
            var invalidFutureDate = new Date();
            invalidFutureDate.setDate(invalidFutureDate.getDate() + 1460);
            vm.pikaday(invalidFutureDate);
            assert.isFalse(vm.pikaday.isValid());
        });
    });
    describe('#requestingEmbargo', () => {
        it('returns false if user chose make public', () => {
            vm.registrationChoice(MAKE_PUBLIC);
            assert.isFalse(vm.requestingEmbargo());
        });
        it('returns true if user chose requests embargo', () => {
            vm.registrationChoice(MAKE_EMBARGO);
            assert.isTrue(vm.requestingEmbargo());
        });
    });
});

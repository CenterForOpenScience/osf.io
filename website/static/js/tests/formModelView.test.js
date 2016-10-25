/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $osf = require('js/osfHelpers');

var formViewModel = require('js/formViewModel');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('formModelView', () => {

    describe('ValidationError', () => {
        it('inherits from Error', () => {
            var validationError = new formViewModel.ValidationError();
            assert.instanceOf(validationError, Error);
        });

        it('sets defaults properly', () => {
            var validationError = new formViewModel.ValidationError();
            assert.equal(validationError.message, []);
            assert.equal(validationError.header, 'Error');
            assert.equal(validationError.level, 'warning');
        });
    });

    describe.skip('ViewModel', () => {
        var vm;

        beforeEach(() => {
            vm = new formViewModel.FormViewModel();
        });

        it('throws Error for unimplemented isValid', () => {
             assert.throw(vm.isValid, Error, 'FormViewModel subclass must implement isValid');
        });

        describe('submit', () => {
            var isValidStub;

            beforeEach(() => {
                isValidStub = sinon.stub(vm, 'isValid');
            });

            afterEach(() => {
                isValidStub.restore();
            });

            it('returns true if isValid', () => {
                isValidStub.returns(true);
                var result = vm.submit();
                assert.isTrue(result);
            });

            it('calls growl if not isValid', () => {
                var growlSpy = new sinon.stub($osf, 'growl');
                isValidStub.throws(new formViewModel.ValidationError(['pewpewpew']));
                vm.submit();
                assert.isTrue(growlSpy.called);
                growlSpy.restore();
            });
        });
    });
});

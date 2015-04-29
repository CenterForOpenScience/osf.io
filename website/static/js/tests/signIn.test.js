/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $osf = require('js/osfHelpers');

var signIn = require('js/signIn');
var formViewModel = require('js/formViewModel')

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('signIn', () => {
    describe('ViewModels', () => {

        describe('SignInViewModel', () => {
            var vm;

            var tooShortPassword = 'pass';
            var tooLongPassword = 'asdfasdfasdfasdfasdfasdfasdfasdfasdfasdf';
            var validPassword = 'password';
            var invalidUsername = 'notanemail';
            var validUsername = 'tim@tom.com';

            beforeEach(() => {
                vm = new signIn.ViewModel();
            });

            it('inherit from FormViewModel', () => {
                assert.instanceOf(vm, formViewModel.FormViewModel);
            });

            it('isValid returns true for valid user/pass', () => {
                vm.password(validPassword);
                vm.username(validUsername);
                assert.isTrue(vm.username.isValid());
            });

            it('isValid returns false for invalid user/pass', () => {
                vm.password(tooLongPassword);
                vm.username(invalidUsername);
                assert.isFalse(vm.username.isValid());
            });

            it('invalid email is not valid', () => {
                vm.password(validPassword);
                vm.username(invalidUsername);
                assert.isFalse(vm.username.isValid());
            });


            describe('submit', () => {
                var growlSpy;

                beforeEach(() => {
                    growlSpy = new sinon.stub($osf, 'growl');
                });

                afterEach(() => {
                    growlSpy.restore();
                });
                it('growl called if invalid username', () => {
                    vm.username(invalidUsername);
                    vm.password(validPassword);
                    vm.submit();
                    assert.isTrue(growlSpy.calledOnce);
                });
                it('growl not called with valid username/password', () => {
                    vm.username(validUsername);
                    vm.password(validPassword);
                    vm.submit();
                    assert.isFalse(growlSpy.called);
                });

            });
        });
    });
});


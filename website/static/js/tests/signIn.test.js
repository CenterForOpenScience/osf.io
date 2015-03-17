/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $osf = require('js/osfHelpers');

var signIn = require('../signIn');

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

            it('isValid returns true for valid user/pass', (done) => {
                vm.password(validPassword);
                vm.username(validUsername);
                assert.isTrue(vm.username.isValid());
                done();
            });

            it('isValid returns false for invalid user/pass', (done) => {
                vm.password(tooLongPassword);
                vm.username(invalidUsername);
                assert.isFalse(vm.username.isValid());
                done();
            });

            it('invalid email is not valid', () => {
                vm.password(validPassword);
                vm.username(invalidUsername);
                assert.isFalse(vm.username.isValid());
            });

            it('password under 6 chars is invalid', (done) => {
                vm.username(validUsername);
                vm.password(tooShortPassword);
                assert.isFalse(vm.password.isValid());
                done();
            });

            it('password over 35 chars is invalid', (done) => {
                vm.username(validUsername);
                vm.password(tooLongPassword);
                assert.isFalse(vm.isValid());
                done();
            });

            describe('submit', () => {
                var growlSpy;

                beforeEach(() => {
                    growlSpy = new sinon.stub($osf, 'growl');
                });

                afterEach(() => {
                    growlSpy.restore();
                });

                it('growl called if password too short', () => {
                    vm.username(validUsername);
                    vm.password(tooShortPassword);
                    vm.submit();
                    assert.isTrue(growlSpy.calledOnce);
                });
                it('growl called if password too long', () => {
                    vm.username(validUsername);
                    vm.password(tooLongPassword);
                    vm.submit();
                    assert.isTrue(growlSpy.calledOnce);
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


/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';

var $osf = require('js/osfHelpers');

var assert = require('chai').assert;
var faker = require('faker');
var utils = require('./utils');

var Raven = require('raven-js');
var registrationRetraction = require('js/registrationRetraction');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('registrationRetraction', () => {
    sinon.collection.restore();
    describe('ViewModels', () => {

        describe('RegistrationRetractionViewModel', () => {
            var vm;
            var invalidJustification = faker.lorem.paragraphs(50);
            var invalidConfirmationText = 'abcd';
            var submitUrl = '/project/abcdef/withdraw/';
            var invalidSubmitUrl = '/notAnEndpoint/';
            var redirectUrl = '/project/abdef/';
            var response = {redirectUrl: redirectUrl};
            var endpoints = [
                {
                    method: 'POST',
                    url: submitUrl,
                    response: response
                },
                {
                    method: 'POST',
                    url: invalidSubmitUrl,
                    response: {},
                    status: 500
                }
            ];
            var server;

            before(() => {
                server = utils.createServer(sinon, endpoints);
            });

            after(() => {
                server.restore();
            });

            var onSubmitSuccessStub;
            beforeEach(() => {
                vm = new registrationRetraction.ViewModel(submitUrl);
                onSubmitSuccessStub = sinon.stub(vm, 'onSubmitSuccess');
            });

            afterEach(() => {
                onSubmitSuccessStub.restore();
            });

            it('non-matching registration title is invalid', () => {
                vm.confirmationText(invalidConfirmationText);
                assert.isFalse(vm.confirmationText.isValid());
            });

            it('matching registration title is valid', () => {
                vm.confirmationText(vm.confirmationString);
                assert.isTrue(vm.confirmationText.isValid());
            });

            describe('submit', () => {
                var postSpy;
                var changeMessageSpy;

                beforeEach(() => {
                    postSpy = new sinon.spy($osf, 'postJSON');
                    changeMessageSpy = new sinon.spy(vm, 'changeMessage');
                });

                afterEach(() => {
                    postSpy.restore();
                    changeMessageSpy.restore();
                });

                it('calls changeMessage if invalid confirmation text submitted', () => {
                    vm.confirmationText(invalidConfirmationText);
                    vm.submit();
                    assert.calledOnce(changeMessageSpy);
                    assert.notCalled(postSpy);
                });
                it('calls changeMessage if justification is too long', () => {
                    vm.confirmationText(vm.confirmationString);
                    vm.justification(invalidJustification);
                    vm.submit();
                    assert.calledOnce(changeMessageSpy);
                    assert.notCalled(postSpy);
                });
                it('submits successfully with valid confirmation text', (done) => {
                    vm.confirmationText(vm.confirmationString);
                    vm.submit().always(() => {
                        assert.equal(response.redirectUrl, redirectUrl);
                        assert.called(onSubmitSuccessStub);
                        assert.called(postSpy);
                        assert.notCalled(changeMessageSpy);
                        done();
                    });
                });

                it('logs error with Raven if submit fails', (done) => {
                    sinon.collection.restore();
                    vm = new registrationRetraction.ViewModel(invalidSubmitUrl);
                    var onSubmitErrorSpy = new sinon.spy(vm, 'onSubmitError');
                    var ravenStub = new sinon.stub(Raven, 'captureMessage');

                    vm.confirmationText(vm.confirmationString);
                    vm.submit().always((xhr) => {
                        assert.equal(xhr.status, 500);
                        assert.equal(response.redirectUrl, redirectUrl);
                        assert.called(onSubmitErrorSpy);
                        assert.called(postSpy);
                        onSubmitErrorSpy.restore();
                        ravenStub.restore();
                        done();
                    });
                });

            });
        });
    });
});

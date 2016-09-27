/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');

var $ = require('jquery');
require('jquery-qrcode');

var osfHelpers = require('js/osfHelpers');

var ViewModel = require('../twoFactorUserConfig')._ViewModel;

var DISABLED = {
    is_enabled: false,
    is_confirmed: false,
    secret: '',
    urls: {
        enable: faker.internet.ip()
    }
};
var ENABLED_AND_UNCONFIRMED = {
    is_enabled: true,
    is_confirmed: false,
    secret: '',
    urls: {
        otpauth: faker.internet.ip(),
        disable: faker.internet.ip()
    }
};
var ENABLED_AND_CONFIRMED = {

};
var SELECTOR = '#myQRCode';

describe('Two-factor User Config', () => {
    describe('ViewModel', () => {
        var settingsUrl = faker.internet.ip();
        var vm = new ViewModel(settingsUrl, SELECTOR);

        describe('#initialize', () => {
            var fetchFromServerStub;
            var updateFromDataSpy;
            before(() => {
                fetchFromServerStub = new sinon.stub(vm, 'fetchFromServer', function() {
                    var ret = $.Deferred();
                    ret.resolve(DISABLED);
                    return ret.promise();
                });
                updateFromDataSpy = sinon.spy(vm, 'updateFromData');
            });
            after(() => {
                vm.fetchFromServer.restore();
                vm.updateFromData.restore();
            });
            it('makes a call to fetchFromServer, and updates the VM state with the result', (done) => {
                vm.initialize()
                    .always(function() {
                        assert.calledOnce(fetchFromServerStub);
                        assert.calledWith(updateFromDataSpy, DISABLED);
                        done();
                    });
            });
        });
        describe('#updateFromData', () => {
            it('updates the VM state with the passed data', () => {
                vm.isEnabled(true);
                vm.isConfirmed(true);
                vm.secret('SUPER SECRET');
                vm.urls = 'SOME URLS';
                vm.updateFromData(DISABLED);
                assert.isFalse(vm.isEnabled());
                assert.isFalse(vm.isConfirmed());
                assert.equal(DISABLED.secret, vm.secret());
                assert.deepEqual(DISABLED.urls, vm.urls);
            });
           
            /*
             TODO: it would be nice to have a sinon.spy on the $() method here, 
             but this is proving problematc in practice. 
             */
            var qrcodeStub;
            before(() => {
                qrcodeStub = new sinon.stub($.prototype, 'qrcode');
            });
            after(() => {
                $.prototype.qrcode.restore();
            });
            it('calls jQuery(selector).qrcode(url) on the passed selector with the fetched otpauth url if enabled', () => {
                // set VM state to DISBALED
                vm.updateFromData(DISABLED);
                vm.updateFromData(ENABLED_AND_UNCONFIRMED);
                assert.calledWith(qrcodeStub, ENABLED_AND_UNCONFIRMED.urls.otpauth);
            });            
        });
        describe('#fetchFromServer', () => {
            var endpoints = [
                {
                    url: settingsUrl,
                    method: 'GET',
                    response: {
                        result: DISABLED
                    }
                }
            ];
            var server;
            var callback;
            before(() => {
                callback = sinon.spy();
                server = utils.createServer(sinon, endpoints);
            });
            after(() => {
                server.restore();
            });
            it("makes a get request to the settingsUrl and resolves its promised with the unwrapped 'result'", (done) => {
                vm.fetchFromServer()
                    .done(callback)
                    .always(function() {
                        assert.calledWith(callback, DISABLED);
                        done();
                    });
            });
        });
        describe('#changeMessage', () => {
            it('updates the VM\'s message and message CSS class', () => {
                vm.message('');
                vm.messageClass('some-class');
                var msg = 'Such success!';
                var cls = 'text-success';
                vm.changeMessage(msg, cls);
                assert.equal(vm.message(), msg);
                assert.equal(vm.messageClass(), cls);
                msg = 'Much fail!';
                cls = 'text-error';
                vm.changeMessage(msg, cls);
                assert.equal(vm.message(), msg);
                assert.equal(vm.messageClass(), cls);
            });
            var timer;
            before(() => {
                timer = sinon.useFakeTimers();
            });
            after(() => {
                timer.restore();
            });
            it('... and removes the message after a timeout if supplied', () => {
                vm.message('');
                vm.messageClass('text-info');
                var oldMsg = vm.message();
                var oldCls = vm.messageClass();
                var msg = 'Such success!';
                var cls = 'text-success';
                vm.changeMessage(msg, cls, 200);
                timer.tick(201);
                assert.equal(vm.message(), oldMsg);
                assert.equal(vm.messageClass(), oldCls);
            });
        });
        describe('#submitSettings', () => {
            var server;
            var callback;
            before(() => {
                server = sinon.fakeServer.create();                    
                server.respondWith('PUT', settingsUrl, function(xhr) { 
                    // An echo endpoint
                    xhr.respond(200, {'Content-Type': 'application/json'}, xhr.requestBody);
                });
                callback = sinon.spy();
            });
            after(() => {
                server.restore();
            });
            it("makes a PUT request containing the VM's tfaCode to the settingsUrl passed on instantiation", (done) => {
                var code = faker.finance.account();
                vm.tfaCode(code);
                vm.submitSettings()
                    .done(callback)
                    .always(function() {
                        assert.calledWith(callback, {
                            code: code
                        });
                        done();
                    });
                server.respond();
            });               
        });
        describe('#disableTwofactorConfirm', () => {
            var server;
            var serverSpy;
            before(() => {
                serverSpy = sinon.spy();
                server = sinon.fakeServer.create();
                server.respondWith('DELETE', 
                                   ENABLED_AND_UNCONFIRMED.urls.disable, 
                                   function(xhr) {
                                       serverSpy();
                                       xhr.respond(200, {'Content-Type': 'application/json'}, '{}');
                                   });                
            });
            after(() => {
                server.restore();
            });
            it('sends a DELETE request to the disable url, sets isEnabled to false, sets isConfirmed to false', (done) => {
                vm.updateFromData(ENABLED_AND_UNCONFIRMED);
                vm.disableTwofactorConfirm()
                    .always(function() {
                        assert.calledOnce(serverSpy);
                        assert.isFalse(vm.isEnabled());
                        assert.isFalse(vm.isConfirmed());
                        done();
                    });
                server.respond();
            });
        });
        describe('#enableTwofactorConfirm', () => {
            var server;
            var serverSpy;
            var updateFromDataStub;
            before(() => {
                vm.updateFromData(DISABLED);
                serverSpy = sinon.spy();
                server = sinon.fakeServer.create();                
                server.respondWith('POST', DISABLED.urls.enable, function(xhr) {
                    serverSpy();
                    xhr.respond(200, {'Content-Type': 'application/json'}, JSON.stringify({result: ENABLED_AND_UNCONFIRMED}));
                });
                updateFromDataStub = sinon.stub(vm, 'updateFromData');
            });
            after(() => {
                server.restore();
                vm.updateFromData.restore();
            });
            it('sends a POST request to the enable url and calls updateFromData with the response', (done) => {
                vm.enableTwofactorConfirm()
                    .always(function() {
                        assert.called(serverSpy);
                        assert.calledWith(updateFromDataStub, ENABLED_AND_UNCONFIRMED);
                        done();
                    });
                server.respond();
            });
        });
    });
});

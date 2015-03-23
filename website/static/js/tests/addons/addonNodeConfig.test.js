/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var ZeroClipboard = require('zeroclipboard');
var AddonNodeConfigVM = require('js/addonNodeConfig')._AddonNodeConfigViewModel;
var testUtils = require('./folderPickerTestUtils.js');

var makeEmailList = function(n) {
    var ret = [];
    for (var i = 0; i < n; i++){
        ret.push(faker.internet.email());
    }
    return ret;
};
var makeAccountList = function() {
    var accounts = [];
    for (var i = 0; i < 3; i++){
        accounts.push({
            display_name: faker.name.findName(),
            id: faker.finance.account()
        });
    }
    return accounts;
};

describe('AddonNodeConfig', () => {
    describe('AddonFolderPickerViewModel', () => {
        var settingsUrl = '/api/v1/12345/addon/config/';
        var onPickFolderSpy = sinon.spy();
        var opts = {
            onPickFolder: onPickFolderSpy
        };
        var vm = new AddonNodeConfigVM('Fake Addon', settingsUrl, '#fakeAddonScope', '#fakeAddonPicker', opts);
        
        describe('#constructor', () => {
            it('applies overrides from the opts param if supplied', () => {
                vm.treebeardOptions.onPickFolder();
                assert.calledOnce(opts.onPickFolder);
            });
        });

        describe('#toggleShare', () => {
            var stub;
            before(() => {
                stub = sinon.stub(vm, 'activateShare');
            });
            after(() => {
                vm.activateShare.restore();
            });
            it('toggles the share display and calls activateShare if hidden', () => {
                vm.currentDisplay(null);
                vm.toggleShare();    
                assert.equal(vm.currentDisplay(), vm.SHARE);
                assert.calledOnce(stub);
            });
        });
        describe('#fetchEmailList', () => {
            var emailsUrl = faker.internet.ip();
            var emails = makeEmailList(10);
            var endpoints = [{
                url: emailsUrl,
                method: 'GET',
                response: {
                    results: {
                        emails: emails
                    }
                }
            }];
            var server;
            before(() => {
                server = utils.createServer(sinon, endpoints);
            });
            after(() => {
                server.restore();
            });
            it('makes a GET request to the "emails" url passed from settings if the email list has not been fetched', (done) => {
                var data = testUtils.makeFakeData();
                data.urls.emails = emailsUrl;
                vm.updateFromData(data)
                    .always(function() {
                        vm.fetchEmailList()
                            .then(function(emails) {
                                assert.deepEqual(endpoints[0].response.results.emails, emails);
                                done();
                            });
                    });
            });
            it('returns a promise that resolves to the list of emails if the email list has already been fetched', (done) => {
                var email = faker.internet.email();
                vm.emails([email]);
                vm.loadedEmails(true);
                vm.fetchEmailList()
                    .done(function(emails){
                        assert.equal(emails[0], email);
                        done();
                    });
            });
        });
        describe('#activateShare', () => {
            var fetchEmailListStub;
            before(() => {
                fetchEmailListStub = sinon.stub(vm, 'fetchEmailList', function() {
                    var def = $.Deferred();
                    def.resolve(makeEmailList(10));
                    return def.promise();
                });
            });
            after(() => {
                vm.fetchEmailList.restore();
            });
            it('activates the share UI and makes a call to fetchEmailList', () => {
                vm.activateShare();
                assert.calledOnce(fetchEmailListStub);
            });
        });
        describe('#fetchAccounts', () => {
            var accountsUrl = faker.internet.ip();
            var accounts = makeAccountList();
            var endpoints = [{
                url: accountsUrl,
                method: 'GET',
                response: {
                    accounts: accounts
                }
            }];
            var server;
            before(() => {
                server = utils.createServer(sinon, endpoints);
            });
            after(() => {
                server.restore();
            });
            it('makes a GET request to the "accounts" url passed in settings, and returns a promise that resolves to that value', () => {
                var data = testUtils.makeFakeData();
                data.urls.accounts = accountsUrl;
                vm.updateFromData(data)
                .always(function(){
                    vm.fetchAccounts()
                        .done(function(fetched) {
                            assert.deepEqual(fetched, endpoints[0].response.accounts);
                        });
                });
            });
        });
        describe('#updateAccounts', () => {
            it('calls fetchAccounts and updates the VM with the result', (done) => {
                var accounts = makeAccountList();
                var stub = sinon.stub(vm, 'fetchAccounts', 
                                      function() {
                                          var ret = $.Deferred();
                                          ret.resolve(accounts);
                                          return ret.promise();
                                      });
                vm.accounts([]);
                vm.updateAccounts()
                    .always(function(){
                        assert.deepEqual(accounts.map(
                            function(a){ 
                                return {
                                    name: a.display_name,
                                    id: a.id
                                };
                            }), vm.accounts());
                    });
            });
        });
        describe('#connectAccount', () => {
            it('opens a new window (tab) pointed at the "auth" url passed in settings', (done) => {
                var data = testUtils.makeFakeData();
                var authUrl = faker.internet.ip();
                data.urls.auth = authUrl;
                var stub = sinon.stub(window, 'open');
                vm.updateFromData(data)
                    .always(function() {
                        vm.connectAccount();
                        assert.calledWith(stub, authUrl);
                        window.open.restore();
                        done();
                    });
            });
        });
    });
});

/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var ZeroClipboard = require('zeroclipboard');
var CitationsNodeConfigVM = require('js/citationsNodeConfig')._CitationsNodeConfigViewModel;
var testUtils = require('./folderPickerTestUtils.js');
var FolderPicker = require('js/folderpicker');

var makeAccountList = function() {
    var accounts = [];
    for (var i = 0; i < 3; i++) {
        accounts.push({
            display_name: faker.name.findName(),
            id: faker.finance.account()
        });
    }
    return accounts;
};
describe('CitationsNodeConfig', () => {
    describe('CitationsFolderPickerViewModel', () => {
        var settingsUrl = '/api/v1/12345/addon/config/';
        var onPickFolderSpy = sinon.spy();
        var opts = {
            onPickFolder: onPickFolderSpy
        };
        var vm = new CitationsNodeConfigVM('Fake Addon', settingsUrl, '#fakeAddonScope', '#fakeAddonPicker', opts);
        var activateStub;
        before(() => {
            // Never actually call doActivatePicker
            activateStub = sinon.stub(vm, 'doActivatePicker');        
        });
        after(() => {
            activateStub.restore();
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
            it('makes a GET request to the "accounts" url passed in settings, and returns a promise that resolves to that value', (done) => {
                var data = testUtils.makeFakeData();
                data.urls.accounts = accountsUrl;
                vm.updateFromData(data)
                    .always(function() {
                        vm.fetchAccounts()
                            .always(function(fetched) {
                                assert.deepEqual(fetched, endpoints[0].response.accounts);
                                done();
                            });
                    });
            });
        });
        describe('#updateAccounts', () => {
            var accounts;
            var stub;
            before(() => {
                accounts = makeAccountList();
                stub = sinon.stub(vm, 'fetchAccounts',
                    function() {
                        var ret = $.Deferred();
                        ret.resolve(accounts);
                        return ret.promise();
                    });
            });
            after(() => {
                vm.fetchAccounts.restore();
            });

            it('calls fetchAccounts and updates the VM with the result', (done) => {
                vm.accounts([]);
                vm.updateAccounts()
                    .always(function() {
                        accounts = accounts.map(
                            function(a) {
                                return {
                                    name: a.display_name,
                                    id: a.id
                                };
                            });
                        assert.deepEqual(accounts, vm.accounts());
                        done();
                    });
            });
        });
        describe('#connectAccount', () => {
            var stub;
            before(() => {
                stub = sinon.stub(window, 'open');
            });
            after(() => {
                window.open.restore();
            });

            it('opens a new window (tab) pointed at the "auth" url passed in settings', (done) => {
                var data = testUtils.makeFakeData();
                var authUrl = faker.internet.ip();
                data.urls.auth = authUrl;
                vm.updateFromData(data)
                    .always(function() {
                        vm.connectAccount();
                        assert.calledWith(stub, authUrl);
                        done();
                    });
            });
        });
        describe('#connectExistingAccount', () => {
            var stub;
            var data;
            var importAuthUrl;
            before(() => {
                importAuthUrl = faker.internet.ip();
                data = testUtils.makeFakeData();
                data.urls.importAuth = importAuthUrl;
                stub = sinon.stub($osf, 'putJSON', function() {
                    var ret = $.Deferred();
                    ret.resolve({
                        result: data
                    });
                    return ret.promise();
                });
            });
            after(() => {
                $osf.putJSON.restore();
            });
            it('makes a PUT request to the the "importAuth" url passed in settings sending the passed account_id as data', (done) => {
                vm.updateFromData(data)
                    .always(function() {
                        var account_id = faker.finance.account();
                        vm.connectExistingAccount(account_id)
                            .always(function() {
                                assert.calledWith(stub,
                                                  importAuthUrl,
                                                  {
                                                      external_account_id: account_id
                                                  });
                                done();
                            });
                    });
            });
        });
    });
});

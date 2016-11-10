/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');
var Raven = require('raven-js');
var oop = require('js/oop');
var ko = require('knockout');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

var FolderPickerNodeConfigVM = require('js/folderPickerNodeConfig');
var FolderPicker = require('js/folderpicker');
var testUtils = require('./folderPickerTestUtils.js');

var onPickFolderSpy = new sinon.spy();
var resolveLazyloadUrlSpy = new sinon.spy();
var TestSubclassVM = oop.extend(FolderPickerNodeConfigVM, {
    constructor: function(addonName, url, selector, folderPicker) {
        this.super.constructor.call(this, addonName, url, selector, folderPicker);
        this.customField = ko.observable('');

        this.messages.submitSettingsSuccess = ko.pureComputed(function(){
            return 'SUCCESS';
        });
    },
    _updateCustomFields: function(settings) {
        this.customField(settings.customField);
    },
    _serializeSettings: function(settings) {
        return this.folder().name.toUpperCase();
    }
});

describe.skip('FolderPickerNodeConfigViewModel', () => {

    var settingsUrl = '/api/v1/12345/addon/config/';
    var endpoints = [{
        method: 'GET',
        url: settingsUrl,
        response: {
            result: {
                ownerName: faker.name.findName(),
                userisOwner: true,
                userHasAuth: true,
                validCredentials: true,
                nodeHasAuth: true,
                urls: {
                    owner: '/abc123/',
                    config: settingsUrl
                }
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

    describe('ViewModel', () => {
        var vm;
        var doActivatePickerStub;
        var hardReset = () => {
            vm = new TestSubclassVM('Fake Addon', settingsUrl, '#fakeAddonScope', '#fakeAddonPicker');
            doActivatePickerStub = sinon.stub(vm, 'doActivatePicker');
        };
        before(hardReset);
        after(() => {
           vm.doActivatePicker.restore();
        });
        afterEach(() => {
            doActivatePickerStub.reset();
        });

        describe('#showImport', () => {
            var reset = () => {
                vm.loadedSettings(true);
                vm.nodeHasAuth(false);
                vm.userHasAuth(true);
            };
            it('shows the import button when the User has auth, the Node doesn\'t have auth, and the VM has loaded settings', () => {
                reset();
                assert.isTrue(vm.showImport());
            });
            it('... and it doesn\'t show the import button otherwise', () => {
                reset();
                vm.loadedSettings(false);
                assert.isFalse(vm.showImport());
                reset();
                vm.nodeHasAuth(true);
                assert.isFalse(vm.showImport());
                reset();
                vm.userHasAuth(false);
                assert.isFalse(vm.showImport());
                reset();
                vm.loadedSettings(false);
                vm.nodeHasAuth(true);
                vm.userHasAuth(false);
                assert.isFalse(vm.showImport());
            });
        });
        describe('#showSettings', () => {
            var reset = () => {
                vm.nodeHasAuth(true);
            };
            it('shows settings if the Node has auth', () => {
                reset();
                assert.isTrue(vm.showSettings());
            });
            it('... and doesn\'t show settings otherwise', () => {
                reset();
                vm.nodeHasAuth(false);
                assert.isFalse(vm.showSettings());
            });
        });
        describe('#showTokenCreateButton', () => {
            var reset = () => {
                vm.userHasAuth(false);
                vm.nodeHasAuth(false);
                vm.loadedSettings(true);
            };
            it('shows the token create button if the User doesn\'t have auth, the Node doesn\'t have auth, and the VM has loaded settings', () => {
                reset();
                assert.isTrue(vm.showTokenCreateButton());
            });
            it('... and doesn\'t show the token create button otherwise', () => {
                reset();
                vm.userHasAuth(true);
                assert.isFalse(vm.showTokenCreateButton());
                reset();
                vm.nodeHasAuth(true);
                assert.isFalse(vm.showTokenCreateButton());
                reset();
                vm.loadedSettings(false);
                assert.isFalse(vm.showTokenCreateButton());
                reset();
                vm.userHasAuth(true);
                vm.nodeHasAuth(true);
                vm.loadedSettings(false);
                assert.isFalse(vm.showTokenCreateButton());
            });
        });
        describe('#folderName', () => {
            it('returns the value of the name property of the currently set folder when the Node has auth', () => {
                vm.nodeHasAuth(true);
                vm.folder({
                    name: null,
                    id: null
                });
                assert.equal(vm.folderName(), '');
                var name = faker.hacker.noun();
                vm.folder({
                    name: name,
                    id: faker.finance.account()
                });
                assert.equal(vm.folderName(), name);
            });
            it('... and returns "" otherwise', () => {
                vm.nodeHasAuth(false);
                assert.equal(vm.folderName(), '');
            });
        });
        describe('#selectedFolderName', () => {
            it('returns the selected folder\'s name if set else "None" when the User is owner', () => {
                vm.userIsOwner(true);
                vm.selected({
                    name: null,
                    id: null
                });
                assert.equal(vm.selectedFolderName(), 'None');
                var name = faker.hacker.noun();
                assert.notEqual(name, 'None');
                vm.selected({
                    name: name,
                    id: faker.finance.account()
                });
                assert.equal(vm.selectedFolderName(), name);
            });
            it('... and returns an empty string otherwise', () => {
                vm.userIsOwner(false);
                assert.equal(vm.selectedFolderName(), '');
            });
        });
        describe('#changeMessage', () => {
            var reset = () => {
                vm.resetMessage();
            };
            it('updates the VM\'s message and message CSS class', () => {
                reset();
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
                reset();
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
        describe('#updateFromData', () => {
            var spy;
            before(() => {
                spy = sinon.spy(vm, 'fetchFromServer');
            });
            after(() => {
                vm.fetchFromServer.restore();
            });

            it('makes a call to fetchFromServer if no data passed as an argument', (done) => {
                vm.updateFromData()
                    .always(function() {
                        assert.calledOnce(spy);
                        done();
                    });
            });
            var data = testUtils.makeFakeData();
            it('updates the VM with data if data passed as argument', (done) => {
                vm.updateFromData(data)
                    .always(function() {
                        assert.equal(vm.nodeHasAuth(), data.nodeHasAuth);
                        assert.equal(vm.userHasAuth(), data.userHasAuth);
                        assert.equal(vm.userIsOwner(), data.userIsOwner);
                        assert.deepEqual(vm.folder(), data.folder);
                        assert.equal(vm.ownerName(), data.ownerName);
                        assert.deepEqual(vm.urls(), data.urls);
                        done();
                    });
            });
            it('... and updates the custom fields requested in \'_updateCustomFields\'', (done) => {
                var customField = faker.hacker.noun();
                data.customField = customField;
                vm.updateFromData(data)
                    .always(function() {
                        assert.equal(vm.customField(), customField);
                        done();
                    });
            });
        });
        describe('#fetchFromServer', () => {
            var data = testUtils.makeFakeData();
            var endpoints = [{
                method: 'GET',
                url: settingsUrl,
                response: {
                    result: data
                }
            }];
            var server;
            before(() => {
                server = utils.createServer(sinon, endpoints);
            });
            after(() => {
                server.restore();
            });
            it('makes GET request to the passed settings url returns a promise that resolves to the response', (done) => {
                vm.fetchFromServer()
                    .always(function(resp) {
                        assert.deepEqual(resp, data);
                        done();
                    });
            });
        });
        describe('#submitSettings', () => {
            var data = testUtils.makeFakeData();
            data.urls.view = faker.internet.ip();
            var configUrl = faker.internet.ip();
            var endpoints = [{
                method: 'PUT',
                url: configUrl,
                response: {
                    result: data
                }
            }];
            var server;
            var spy;
            before(() => {
                server = utils.createServer(sinon, endpoints);
                spy = sinon.spy($osf, 'putJSON');
            });
            after(() => {
                server.restore();
                $osf.putJSON.restore();
            });
            data.urls.config = configUrl;
            it('serializes the VM state and sends a PUT request to the \'config\' url passed in settings', (done) => {
                hardReset();
                vm.updateFromData(data)
                    .always(function() {
                        vm.submitSettings()
                            .always(function() {
                                assert.calledWith(spy, data.urls.config, vm.folder().name.toUpperCase());
                                done();
                            });
                    });
            });
        });
        describe('#_importAuthConfirm', () => {
            var importAuthUrl = faker.internet.ip();
            var endpoints = [{
                method: 'PUT',
                url: importAuthUrl,
                response: {}
            }];
            var server;
            var putJSONSpy;
            var activatePickerSpy;
            before(() => {
                hardReset();
                server = utils.createServer(sinon, endpoints);
                putJSONSpy = sinon.spy($osf, 'putJSON');
                activatePickerSpy = sinon.spy(vm, 'activatePicker');
            });
            after(() => {
                server.restore();
                $osf.putJSON.restore();
                activatePickerSpy.restore();
            });
            var data = testUtils.makeFakeData();
            data.urls.importAuth = importAuthUrl;
            it('sends a PUT request to the \'importAuth\' url passed in settings, calls updateFromData with the response, and calls activatePicker', (done) => {
                vm.updateFromData(data)
                    .always(function() {
                        vm._importAuthConfirm()
                            .always(function() {
                                assert.calledWith(
                                    putJSONSpy,
                                    importAuthUrl,
                                    {}
                                );
                                assert.calledOnce(activatePickerSpy);
                                done();
                            });
                    });
            });
        });

        describe('#destroyPicker', () => {

            it('can be called if folder picker is not initialized', () => {
                vm.folderpicker = null;
                // No errors when destoryPicker is called
                vm.destroyPicker();
            });
        });

        describe('#_deauthorizeConfirm', () => {
            var deleteUrl = faker.internet.ip();
            var endpoints = [{
                url: deleteUrl,
                method: 'DELETE',
                response: {}
            }];
            var server;
            var spy;
            var destroyPickerStub;
            before(() => {
                hardReset();
                server = utils.createServer(sinon, endpoints);
                spy = sinon.spy($, 'ajax');
                destroyPickerStub = sinon.stub(vm, 'destroyPicker');
            });
            after(() => {
                server.restore();
                $.ajax.restore();
                vm.destroyPicker.restore();
            });
            var data = testUtils.makeFakeData();
            data.urls.deauthorize = deleteUrl;
            it('sends a DELETE request to the \'deauthorize\' url passed in settings', (done) => {
                vm.updateFromData(data)
                    .always(function() {
                        vm._deauthorizeConfirm()
                            .always(function() {
                                assert.calledWith(
                                    spy,
                                    {
                                        url: deleteUrl,
                                        type: 'DELETE'
                                    }
                                );
                                done();
                            });
                    });
            });
        });
        describe('#togglePicker', () => {
            it('shows the folder picker and calls activatePicker if hidden', () => {
                vm.currentDisplay(null);
                var spy = sinon.spy(vm, 'activatePicker');
                vm.togglePicker();
                assert.calledOnce(spy);
                assert.equal(vm.currentDisplay(), vm.PICKER);
                vm.activatePicker.restore();
            });
            it('hides the folder picker and cancels the selection if visible', () => {
                vm.currentDisplay(vm.PICKER);
                var spy = sinon.spy(vm, 'cancelSelection');
                vm.togglePicker();
                assert.calledOnce(spy);
                assert.isNull(vm.currentDisplay());
                vm.cancelSelection.restore();
            });
        });
        describe('#treebeardOptions', () => {
            it('throws an Error if the Subclass does not override the default \'resolveLazyloadUrl\'', () => {
                var broken = new TestSubclassVM('Fake Addon', settingsUrl, '#fakeAddonScope', '#fakeAddonPicker');
                assert.throw(broken.treebeardOptions.resolveLazyloadUrl, 'Subclasses of FolderPickerViewModel must implement a "resolveLazyloadUrl(item)" method');
            });
            it('throws an Error if the Subclassess does not override the default \'onPickFolder\'', () => {
                var broken = new TestSubclassVM('Fake Addon', settingsUrl, '#fakeAddonScope', '#fakeAddonPicker');
                assert.throw(broken.treebeardOptions.onPickFolder, 'Subclasses of FolderPickerViewModel must implement a "onPickFolder(evt, item)" method');
            });
        });
        describe('#activatePicker', () => {
            it('instantiates a new folderPicker instance if folders have not been loaded', () => {
                var urls = vm.urls();
                urls.folders = faker.internet.ip();
                vm.urls(urls);
                var opts = $.extend({}, {
                    initialFolderPath: vm.folder().path || '',
                    filesData: vm.urls().folders
                }, vm.treebeardOptions);

                vm.loadedFolders(false);
                vm.activatePicker();
                assert.calledOnce(doActivatePickerStub);
            });
        });
    });
});

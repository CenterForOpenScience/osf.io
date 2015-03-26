/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var $ = require('jquery');

var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');

var githubNodeConfigVM = require('../githubNodeConfig')._githubNodeConfigViewModel;

var API_BASE = '/api/v1/12345/github';
var SETTINGS_URL = [API_BASE, 'settings', ''].join('/');
var URLS = {
    create_repo: [API_BASE, 'newrepo', ''].join('/'),
    import_auth: [API_BASE, 'import-auth', ''].join('/'),
    create_auth: [API_BASE, 'authorize', ''].join('/'),
    deauthorize: SETTINGS_URL,
    repo_list: [API_BASE, 'repos', ''].join('/'),
    set_repo: SETTINGS_URL,
    settings: '/settings/addons/'
};
var makeSettingsEndpoint = function(result, urls) {
    return {
        method: 'GET',
        url: SETTINGS_URL,
        response: {
            result: $.extend({}, {
                urls: $.extend({}, URLS, urls)
            }, result)
        }
    };
};

var noop = function() {};
var APITestCase = function(cfg) {
    this.description = cfg.description || '';
    this.endpoint = cfg.endpoint || {
        response: {
            result: {}
        }
    };
    this.expected = this.endpoint.response.result;
    $.extend(this.expected, cfg.data || {});
};
APITestCase.prototype.run = function(test) {
    var tc = this;
    var server;
    tc.before = () => {
        server = utils.createServer(sinon, [tc.endpoint]);
    };
    tc.after = () => {
        server.restore();
    };
    test(tc);
};
var APITestCases = function(test, cases) {
    for (var i = 0; i < cases.length; i++) {
        new APITestCase(cases[i]).run(test);
    }
};

describe('githubNodeConfigViewModel', () => {
    describe('#fetchFromServer', () => {
        new APITestCases(
            function(tc) {
                var expected = tc.expected;
                describe('Case: ' + tc.description, () => {
                    before(tc.before);
                    after(tc.after);
                    it('fetches data from the server and updates its state', (done) => {
                        var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
                        vm.updateFromData()
                            .always(function() {
                                // VM is updated with data from the fake server
                                // observables
                                assert.equal(vm.ownerName(), expected.owner);
                                assert.equal(vm.nodeHasAuth(), expected.node_has_auth);
                                assert.equal(vm.userHasAuth(), expected.user_has_auth);
                                assert.equal(vm.currentRepo(), (expected.repo === null) ? 'None' : '');
                                assert.deepEqual(vm.urls(), expected.urls);
                                done();
                            });
                    });
                    describe('... and after updating computed values work as expected', () => {
                        it('shows settings if Node has auth', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showSettings(), expected.showSettings);
                                    done();
                                });
                        });
                        it('disables settings in User dosen\'t have auth and is not auth owner', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.disableSettings(), expected.disableSettings);
                                    done();
                                });
                        });
                        it('shows the new repo button if User has auth and is auth owner', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showNewRepo(), expected.showNewRepo);
                                    done();
                                });
                        });
                        it('shows the import auth link if User has auth and Node is unauthorized', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showImport(), expected.showImportAuth);
                                    done();
                                });
                        });
                        it('shows the create credentials link if User is unauthorized and Node is unauthorized ', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showCreateCredentials(), expected.showCreateCredentials);
                                    done();
                                });
                        });
                        it('lets User see change repo UI if they are auth owner and Node has auth', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.canChange(), expected.canChange);
                                    done();
                                });
                        });
                        it('allows User to change repos if there are repos to be seleted and repos are not currently being loaded ', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.allowSelectRepo(), expected.allowSelectRepo);
                                    done();
                                });
                        });
                    });
                });
            }, [{
                description: 'Node is unauthorized and User is unauthorized',
                endpoint: makeSettingsEndpoint({
                    node_has_auth: false,
                    user_has_auth: false,
                    user_is_owner: false,
                    owner: null,
                    repo: null
                }),
                data: {
                    showSettings: false,
                    disableSettings: true,
                    showNewRepo: false,
                    showImportAuth: false,
                    showCreateCredentials: true,
                    canChange: false,
                    allowSelectRepo: false
                }
            }, {
                description: 'Node is authorized and User not auth owner',
                endpoint: makeSettingsEndpoint({
                    node_has_auth: true,
                    user_has_auth: false,
                    user_is_owner: false,
                    owner: faker.name.findName(),
                    repo: null,
                    allowSelectRepo: false
                }),
                data: {
                    showSettings: true,
                    disableSettings: true,
                    showNewRepo: false,
                    showImportAuth: false,
                    showCreateCredentials: false,
                    canChange: false,
                    allowSelectRepo: false
                }
            }, {
                description: 'Node is unauthorized and User has auth',
                endpoint: makeSettingsEndpoint({
                    node_has_auth: false,
                    user_has_auth: true,
                    user_is_owner: true,
                    owner: faker.name.findName(),
                    repo: null
                }),
                data: {
                    showSettings: false,
                    disableSettings: false,
                    showNewRepo: true,
                    showImportAuth: true,
                    showCreateCredentials: false,
                    canChange: false,
                    allowSelectRepo: false
                }
            }, {
                description: 'Node is authorized and User is auth owner',
                endpoint: makeSettingsEndpoint({
                    node_has_auth: true,
                    user_has_auth: true,
                    user_is_owner: true,
                    owner: faker.name.findName(),
                    repo: null
                }),
                data: {
                    showSettings: true,
                    disableSettings: false,
                    showNewRepo: true,
                    showImportAuth: false,
                    showCreateCredentials: false,
                    canChange: true,
                    allowSelectRepo: false
                }
            }]);
    });
    describe('#toggleRepo', () => {
        var server;
        var endpoints = [{
                method: 'GET',
                url: URLS.repo_list,
                response: {
                    repos: new Array(10).map(faker.internet.password)
                }
            },
            makeSettingsEndpoint()
        ];
        before(() => {
            server = utils.createServer(sinon, endpoints);
        });
        after(() => {
            server.restore();
        });
        it('shows the repo selector when disabled and if repos aren\'t loaded fetches the list of repos', (done) => {
            var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
            vm.updateFromData()
                .always(function() {
                    vm.showSelect(false);
                    vm.loadedRepoList(false);
                    var spy = sinon.spy(vm, 'fetchRepoList');
                    var promise = vm.toggleSelect();
                    promise.always(function() {
                        assert.isTrue(vm.showSelect());
                        assert.isTrue(vm.loadedRepoList());
                        assert.isAbove(vm.repoList().length, 0);
                        assert(spy.calledOnce);
                        done();
                    });
                });
        });
    });
    describe('#selectRepo', () => {
        var postEndpoint = makeSettingsEndpoint();
        postEndpoint.method = 'POST';
        postEndpoint.response = postEndpoint.response.result;
        var repo = faker.internet.domainWord();
        postEndpoint.response.repo = repo;
        postEndpoint.response.has_repo = true;
        var endpoints = [
            postEndpoint,
            makeSettingsEndpoint()
        ];
        var server;
        before(() => {
            server = utils.createServer(sinon, endpoints);
        });
        after(() => {
            server.restore();
        });
        it('submits the selected repo to the server, and updates data on success', (done) => {
            var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
            vm.updateFromData()
                .always(function() {
                    vm.selectedRepo(repo);
                    var promise = vm.selectRepo();
                    promise.always(function() {
                        assert.equal(vm.currentRepo(), repo);
                        done();
                    });
                });
        });
    });
    describe('Authorization/Authentication: ', () => {
        var deleteEndpoint = makeSettingsEndpoint({
            user_has_auth: true,
            user_is_owner: true,
            node_has_auth: false
        });
        deleteEndpoint.method = 'DELETE';
        deleteEndpoint.response = deleteEndpoint.response.result;
        var importEndpoint = makeSettingsEndpoint({
            node_has_auth: true,
            user_has_auth: true,
            user_is_owner: true
        });
        importEndpoint.method = 'POST';
        importEndpoint.url = URLS.import_auth;
        importEndpoint.response = importEndpoint.response.result;
        var createEndpoint = makeSettingsEndpoint({
            node_has_auth: true,
            user_has_auth: true,
            user_is_owner: true
        });
        createEndpoint.method = 'POST';
        createEndpoint.url = URLS.create_auth;
        createEndpoint.response = createEndpoint.response.result;
        var endpoints = [
            makeSettingsEndpoint({
                user_has_auth: true,
                user_is_owner: true,
                node_has_auth: true
            }),
            deleteEndpoint,
            importEndpoint,
            createEndpoint
        ];
        var server;
        beforeEach(() => {
            server = utils.createServer(sinon, endpoints);
        });
        afterEach(() => {
            server.restore();
        });

        describe('#_deauthorizeNodeConfirm', () => {
            it('makes a delete request to the server and updates settings on success', (done) => {
                var expected = endpoints[1].response;
                var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
                vm.updateFromData()
                    .always(function() {
                        var promise = vm._deauthorizeNodeConfirm();
                        promise.always(function() {
                            assert.equal(vm.userHasAuth(), expected.user_has_auth);
                            assert.equal(vm.nodeHasAuth(), expected.node_has_auth);
                            assert.isFalse(vm.showSettings());
                            assert.isTrue(vm.showImport());
                            done();
                        });
                    });
            });
        });
        describe('#_importAuthConfirm', () => {
            before(() => {
                // Prepare settings endpoint for next test
                endpoints[0].response.result.node_has_auth = false;
            });
            it('makes a POST request to import auth and updates settings on success', (done) => {
                var expected = endpoints[2].response;
                var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
                vm.updateFromData()
                    .always(function() {
                        var promise = vm._importAuthConfirm();
                        promise.always(function() {
                            assert.equal(vm.nodeHasAuth(), expected.node_has_auth);
                            assert.isTrue(vm.showSettings());
                            done();
                        });
                    });
            });
        });
        describe('#createCredentials', () => {
            before(() => {
                // Prepare settings endpoint for next test
                endpoints[0].response.result.node_has_auth = false;
                endpoints[0].response.result.user_has_auth = false;
                endpoints[0].response.result.user_is_owner = false;
                // temporarily disable mock server autoRespond
                server.autoRespond = false;
            });
            after(() => {
                // restore fake server autoRespond
                server.autoRespond = true;
            });
            var expected = endpoints[0].response;
            it('makes a POST request to create auth and updates settings on success', (done) => {
                var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
                vm.updateFromData()
                    .always(function() {
                        var promise = vm.createCredentials();
                        assert.isTrue(vm.creatingCredentials());
                        assert.isFalse(vm.userHasAuth());
                        server.respond();
                        promise.always(function() {
                            assert.isFalse(vm.creatingCredentials());
                            assert.isTrue(vm.userHasAuth());
                            done();
                        });
                    });
            });
        });
    });
    describe('#createRepo', () => {
        var createEndpoint = makeSettingsEndpoint({
            repos: new Array(10).map(faker.internet.password)
        });
        createEndpoint.method = 'POST';
        createEndpoint.url = URLS.create_repo;
        createEndpoint.response = createEndpoint.response.result;
        var endpoints = [
            makeSettingsEndpoint(),
            createEndpoint
        ];

        var server;
        before(() => {
            server = utils.createServer(sinon, endpoints);
        });
        after(() => {
            server.restore();
        });

        it('sends a POST to create repo and on success updates the repo list', (done) => {
            var vm = new githubNodeConfigVM('/api/v1/12345/github/settings/', '', '/12345');
            vm.updateFromData()
                .always(function() {
                    var name = faker.internet.password();
                    vm.createRepo(name)
                        .always(function() {
                            assert.isFalse(vm.creating());
                            assert.notEqual(vm.repoList().indexOf(name.toLowerCase()), -1);
                            done();
                        });
                });
        });
    });
});
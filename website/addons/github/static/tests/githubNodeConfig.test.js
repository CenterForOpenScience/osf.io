/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var $ = require('jquery');

var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');

var githubNodeConfigVM = require('../githubNodeConfig')._githubNodeConfigViewModel;

var API_BASE = '/api/v1/project/12345/github';
var SETTINGS_URL = [API_BASE, 'settings', ''].join('/');
var URLS = {
    accounts: "/api/v1/settings/github/accounts/?pid=12345",
    auth: "/oauth/connect/github/",
    config: "/api/v1/project/12345/github/settings/",
    create_repo: "/api/v1/project/12345/github/repos/",
    deauthorize: "/api/v1/project/12345/github/authorizations/",
    files: "/project/12345/files/",
    importAuth: "/api/v1/project/12345/github/authorizations/",
    repo_list: "/api/v1/project/12345/github/repos/",
    settings: "/settings/addons/"
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
                        var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');
                        vm.updateFromData()
                            .always(function() {
                                // VM is updated with data from the fake server
                                // observables
                                assert.equal(vm.ownerName(), expected.ownerName);
                                assert.equal(vm.nodeHasAuth(), expected.nodeHasAuth);
                                assert.equal(vm.userHasAuth(), expected.userHasAuth);
                                assert.equal(vm.currentRepo(), (expected.repo === null) ? 'None' : '');
                                assert.deepEqual(vm.urls(), expected.urls);
                                done();
                            });
                    });
                    describe('... and after updating computed values work as expected', () => {
                        it('shows settings if Node has auth', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showSettings(), expected.showSettings);
                                    done();
                                });
                        });
                        it('disables settings in User dosen\'t have auth and is not auth owner', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.disableSettings(), expected.disableSettings);
                                    done();
                                });
                        });
                        it('shows the new repo button if User has auth and is auth owner', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showNewRepo(), expected.showNewRepo);
                                    done();
                                });
                        });
                        it('shows the import auth link if User has auth and Node is unauthorized', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showImport(), expected.showImportAuth);
                                    done();
                                });
                        });
                        it('shows the create credentials link if User is unauthorized and Node is unauthorized ', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showCreateCredentials(), expected.showCreateCredentials);
                                    done();
                                });
                        });
                        it('lets User see change repo UI if they are auth owner and Node has auth', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.canChange(), expected.canChange);
                                    done();
                                });
                        });
                        it('allows User to change repos if there are repos to be seleted and repos are not currently being loaded ', (done) => {
                            var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');
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
                    nodeHasAuth: false,
                    userHasAuth: false,
                    userIsOwner: false,
                    ownerName: '',
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
                    nodeHasAuth: true,
                    userHasAuth: false,
                    userIsOwner: false,
                    ownerName: faker.name.findName(),
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
                    nodeHasAuth: false,
                    userHasAuth: true,
                    userIsOwner: true,
                    owneNamer: faker.name.findName(),
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
                    nodeHasAuth: true,
                    userHasAuth: true,
                    userIsOwner: true,
                    ownerName: faker.name.findName(),
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
                    repo_names: new Array(10).map(faker.internet.password),
                    user_names: new Array(10).map(faker.internet.password)
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
            var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');
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
        var user = faker.internet.domainWord();
        var repo = faker.internet.domainWord();
        postEndpoint.response = {'result':{
            repo: repo,
            user: user,
            has_repo: true,
            nodeHasAuth: true,
            userIsOwner: true,
            ownerName: faker.name.findName(),
            urls: {'files': "/project/12345/files/"}
        }};
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
            var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');

            vm.updateFromData()
                .always(function() {
                    vm.selectedRepo(user + " / " + repo);
                    var promise = vm.selectRepo();
                    promise.always(function() {
                        assert.equal(vm.currentRepo(), user + " / " + repo);
                        done();
                    });
                });
        });
    });
    describe('Authorization/Authentication: ', () => {
        var deleteEndpoint = makeSettingsEndpoint({
            'result': {
                repo: faker.internet.domainWord(),
                user: faker.internet.domainWord(),
                has_repo: true,
                nodeHasAuth: false,
                userHasAuth: true,
                userIsOwner: true,
                ownerName: faker.name.findName()
            }
        });
        deleteEndpoint.method = 'DELETE';
        deleteEndpoint.url = URLS.deauthorize;
        deleteEndpoint.response = deleteEndpoint.response.result;
        var importEndpoint = makeSettingsEndpoint({
           'result': {
                repo: faker.internet.domainWord(),
                user: faker.internet.domainWord(),
                has_repo: true,
                nodeHasAuth: true,
                userHasAuth: true,
                userIsOwner: true,
                ownerName: faker.name.findName()
            }
        });
        importEndpoint.method = 'PUT';
        importEndpoint.url = URLS.importAuth;
        importEndpoint.response = importEndpoint.response.result;
        var createEndpoint = makeSettingsEndpoint({
            nodeHasAuth: true,
            userHasAuth: true,
            userIsOwner: true
        });
        createEndpoint.method = 'POST';
        createEndpoint.url = URLS.auth;
        createEndpoint.response = createEndpoint.response.result;
        var endpoints = [
            makeSettingsEndpoint({
                userHasAuth: true,
                userIsOwner: true,
                nodeHasAuth: true
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
                var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');
                vm.updateFromData()
                    .always(function() {
                        var promise = vm._deauthorizeNodeConfirm();
                        promise.always(function() {
                            assert.equal(vm.userHasAuth(), expected.result.userHasAuth);
                            assert.equal(vm.nodeHasAuth(), expected.result.nodeHasAuth);
                            assert.isFalse(vm.showSettings());
                            assert.isTrue(vm.showImport());
                            done();
                        });
                    });
            });
        });
        describe('#importAuth', () => {
            before(() => {
                // Prepare settings endpoint for next tests
                endpoints[0].response.result.nodeHasAuth = false;
            });
            it('makes a POST request to import auth and updates settings on success', (done) => {
                var expected = endpoints[2].response;
                var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');

                vm.updateFromData()
                    .always(function() {
                        debugger;
                        var promise = vm.connectExistingAccount("fakeid");
                        promise.always(function() {
                            assert.equal(vm.nodeHasAuth(), expected.result.nodeHasAuth);
                            assert.isTrue(vm.showSettings());
                            done();
                        });
                    });
            });
        });

    });
    describe('#createRepo', () => {
        var createEndpoint = makeSettingsEndpoint({
            repo_names: new Array(10).map(faker.internet.password),
            user_names: new Array(10).map(faker.internet.password)
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
            var vm = new githubNodeConfigVM('/api/v1/project/12345/github/settings/', '', '/12345');
            vm.updateFromData()
                .always(function() {
                    var name = faker.internet.password();
                    vm.createRepo(name)
                        .always(function() {
                            assert.isFalse(vm.creating());
                            assert.equal("undefined / " + name.toLowerCase(), vm.selectedRepo());
                            done();
                        });
                });
        });
    });
});
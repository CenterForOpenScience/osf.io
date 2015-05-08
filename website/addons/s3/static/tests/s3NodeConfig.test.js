/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var $ = require('jquery');

var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');

var s3NodeConfigVM = require('../s3NodeConfig')._S3NodeConfigViewModel;

var API_BASE = '/api/v1/12345/s3';
var SETTINGS_URL = [API_BASE, 'settings', ''].join('/');
var URLS = {
    create_bucket: [API_BASE, 'newbucket', ''].join('/'),
    import_auth: [API_BASE, 'import-auth', ''].join('/'),
    create_auth: [API_BASE, 'authorize', ''].join('/'),
    deauthorize: SETTINGS_URL,
    bucket_list: [API_BASE, 'buckets', ''].join('/'),
    set_bucket: SETTINGS_URL,
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

describe('s3NodeConfigViewModel', () => {
    describe('#fetchFromServer', () => {
        new APITestCases(
            function(tc) {
                var expected = tc.expected;
                describe('Case: ' + tc.description, () => {
                    before(tc.before);
                    after(tc.after);
                    it('fetches data from the server and updates its state', (done) => {
                        var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
                        vm.updateFromData()
                            .always(function() {
                                // VM is updated with data from the fake server
                                // observables
                                assert.equal(vm.ownerName(), expected.owner);
                                assert.equal(vm.nodeHasAuth(), expected.node_has_auth);
                                assert.equal(vm.userHasAuth(), expected.user_has_auth);
                                assert.equal(vm.currentBucket(), (expected.bucket === null) ? null : '');
                                assert.deepEqual(vm.urls(), expected.urls);
                                done();
                            });
                    });
                    describe('... and after updating computed values work as expected', () => {
                        it('shows settings if Node has auth and credentials are valid', (done) => {
                            var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showSettings(), expected.showSettings);
                                    done();
                                });
                        });
                        it('disables settings in User dosen\'t have auth and is not auth owner', (done) => {
                            var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.disableSettings(), expected.disableSettings);
                                    done();
                                });
                        });
                        it('shows the new bucket button if User has auth and is auth owner', (done) => {
                            var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showNewBucket(), expected.showNewBucket);
                                    done();
                                });
                        });
                        it('shows the import auth link if User has auth and Node is unauthorized', (done) => {
                            var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showImport(), expected.showImportAuth);
                                    done();
                                });
                        });
                        it('shows the create credentials link if User is unauthorized and Node is unauthorized ', (done) => {
                            var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showCreateCredentials(), expected.showCreateCredentials);
                                    done();
                                });
                        });
                        it('lets User see change bucket UI if they are auth owner and Node has auth', (done) => {
                            var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.canChange(), expected.canChange);
                                    done();
                                });
                        });
                        it('allows User to change buckets if there are buckets to be seleted and buckets are not currently being loaded ', (done) => {
                            var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.allowSelectBucket(), expected.allowSelectBucket);
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
                    bucket: null,
                    valid_credentials: false
                }),
                data: {
                    showSettings: false,
                    disableSettings: true,
                    showNewBucket: false,
                    showImportAuth: false,
                    showCreateCredentials: true,
                    canChange: false,
                    allowSelectBucket: false
                }
            }, {
                description: 'Node is authorized and User not auth owner',
                endpoint: makeSettingsEndpoint({
                    node_has_auth: true,
                    user_has_auth: false,
                    user_is_owner: false,
                    owner: faker.name.findName(),
                    bucket: null,
                    valid_credentials: true
                }),
                data: {
                    showSettings: true,
                    disableSettings: true,
                    showNewBucket: false,
                    showImportAuth: false,
                    showCreateCredentials: false,
                    canChange: false,
                    allowSelectBucket: false
                }
            }, {
                description: 'Node is unauthorized and User has auth',
                endpoint: makeSettingsEndpoint({
                    node_has_auth: false,
                    user_has_auth: true,
                    user_is_owner: true,
                    owner: faker.name.findName(),
                    bucket: null,
                    valid_credentials: true
                }),
                data: {
                    showSettings: false,
                    disableSettings: false,
                    showNewBucket: true,
                    showImportAuth: true,
                    showCreateCredentials: false,
                    canChange: false,
                    allowSelectBucket: false
                }
            }, {
                description: 'Node is authorized and User is auth owner',
                endpoint: makeSettingsEndpoint({
                    node_has_auth: true,
                    user_has_auth: true,
                    user_is_owner: true,
                    owner: faker.name.findName(),
                    bucket: null,
                    valid_credentials: true
                }),
                data: {
                    showSettings: true,
                    disableSettings: false,
                    showNewBucket: true,
                    showImportAuth: false,
                    showCreateCredentials: false,
                    canChange: true,
                    allowSelectBucket: false
                }
            }]);
    });
    describe('#toggleBucket', () => {
        var server;
        var endpoints = [{
                method: 'GET',
                url: URLS.bucket_list,
                response: {
                    buckets: new Array(10).map(faker.internet.password)
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
        it('shows the bucket selector when disabled and if buckets aren\'t loaded fetches the list of buckets', (done) => {
            var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
            vm.updateFromData()
                .always(function() {
                    vm.showSelect(false);
                    vm.loadedBucketList(false);
                    var spy = sinon.spy(vm, 'fetchBucketList');
                    var promise = vm.toggleSelect();
                    promise.always(function() {
                        assert.isTrue(vm.showSelect());
                        assert.isTrue(vm.loadedBucketList());
                        assert.isAbove(vm.bucketList().length, 0);
                        assert(spy.calledOnce);
                        done();
                    });
                });
        });
    });
    describe('#selectBucket', () => {
        var postEndpoint = makeSettingsEndpoint();
        postEndpoint.method = 'POST';
        postEndpoint.response = postEndpoint.response.result;
        var bucket = faker.internet.domainWord();
        postEndpoint.response.bucket = bucket;
        postEndpoint.response.has_bucket = true;
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
        it('submits the selected bucket to the server, and updates data on success', (done) => {
            var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
            vm.updateFromData()
                .always(function() {
                    vm.selectedBucket(bucket);
                    var promise = vm.selectBucket();
                    promise.always(function() {
                        assert.equal(vm.currentBucket(), bucket);
                        done();
                    });
                });
        });
    });
    describe('Authorization/Authentication: ', () => {
        var deleteEndpoint = makeSettingsEndpoint({
            user_has_auth: true,
            user_is_owner: true,
            node_has_auth: false,
            valid_credentials: true
        });
        deleteEndpoint.method = 'DELETE';
        deleteEndpoint.response = deleteEndpoint.response.result;
        var importEndpoint = makeSettingsEndpoint({
            node_has_auth: true,
            user_has_auth: true,
            user_is_owner: true,
            valid_credentials: true
        });
        importEndpoint.method = 'POST';
        importEndpoint.url = URLS.import_auth;
        importEndpoint.response = importEndpoint.response.result;
        var createEndpoint = makeSettingsEndpoint({
            node_has_auth: true,
            user_has_auth: true,
            user_is_owner: true,
            valid_credentials: true
        });
        createEndpoint.method = 'POST';
        createEndpoint.url = URLS.create_auth;
        createEndpoint.response = createEndpoint.response.result;
        var endpoints = [
            makeSettingsEndpoint({
                user_has_auth: true,
                user_is_owner: true,
                node_has_auth: true,
                valid_credentials: true                    
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
            it('makes a DELETE request to the server and updates settings on success', (done) => {
                var expected = endpoints[1].response;
                var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
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
                var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
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
                var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
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
    describe('#createBucket', () => {
        var name = faker.internet.password().toLowerCase();
        var buckets = [];
        for (var i = 0; i < 10; i++){
            buckets.push(faker.internet.password());
        }
        buckets.push(name);
        var createEndpoint = {
            method:  'POST',    
            url: URLS.create_bucket,
            response: {
                buckets: buckets
            }
        };
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

        it('sends a POST to create bucket and on success updates the bucket list', (done) => {
            var vm = new s3NodeConfigVM('/api/v1/12345/s3/settings/', '', '/12345');
            vm.updateFromData()
                .always(function() {
                    vm.createBucket(name)
                        .always(function() {
                            assert.isFalse(vm.creating());
                            assert.notEqual(vm.bucketList().indexOf(name), -1);
                            done();
                        });
                });
        });
    });
});

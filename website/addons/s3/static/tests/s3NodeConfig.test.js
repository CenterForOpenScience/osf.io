/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var $ = require('jquery');
var bootbox = require('bootbox');

var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');

var s3NodeConfig = require('../s3NodeConfig');
var s3NodeConfigVM = s3NodeConfig._S3NodeConfigViewModel;
var isValidBucketName = s3NodeConfig._isValidBucketName;

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

var s3ViewModelSettings = {
    url: '/api/v1/12345/s3/settings/',
    encryptUploads: false,
    bucketLocations: {
        '': 'US',
        'EU': 'ES',
        'us-west-1': 'CA',
        'us-west-2': 'OR',
        'ap-northeast-1': 'TO',
        'ap-southeast-1': 'SI',
        'ap-southeast-2': 'SY',
        'cn-north-1': 'BE'
    }
};

describe('s3NodeConfigViewModel', () => {
    describe('isValidBucketName', () => {
        assert.isTrue(isValidBucketName('valid'));
        assert.isFalse(isValidBucketName('not.valid', false));
        assert.isFalse(isValidBucketName('no'));
        assert.isFalse(isValidBucketName(''));
        var chars = [];
        for (var i = 0, len = 64; i < len; i++) {
            chars.push('a');
        }
        var tooLong = chars.join('');
        assert.isFalse(isValidBucketName(tooLong));
    });

    describe('ViewModel', () => {
        it('imports default settings if not given during instantiation', (done) => {
            // Default settings defined in s3NodeConfig.js
            var defaultSettings = {
                url: '',
                encryptUploads: true,
                bucketLocations: {
                    '': 'US Standard',
                    'EU': 'Europe Standard',
                    'us-west-1': 'California',
                    'us-west-2': 'Oregon',
                    'ap-northeast-1': 'Tokyo',
                    'ap-southeast-1': 'Singapore',
                    'ap-southeast-2': 'Sydney',
                    'cn-north-1': 'Beijing'
                }
            };
            var vm = new s3NodeConfigVM('', {});
            vm.updateFromData().always(function() {
                assert.equal(vm.settings.url, defaultSettings.url);
                assert.equal(vm.settings.encryptUploads, defaultSettings.encryptUploads);
                assert.equal(vm.settings.defaultBucketLocationValue, defaultSettings.defaultBucketLocationValue);
                assert.equal(vm.settings.defaultBucketLocationMessage, defaultSettings.defaultBucketLocationMessage);
                done();
            });
        });
        it('uses settings provided during instantiation', (done) => {
           var vm = new s3NodeConfigVM('', s3ViewModelSettings);
            vm.updateFromData().always(function() {
                assert.equal(vm.settings.url, s3ViewModelSettings.url);
                assert.equal(vm.settings.encryptUploads, s3ViewModelSettings.encryptUploads);
                assert.equal(vm.settings.defaultBucketLocationValue, s3ViewModelSettings.defaultBucketLocationValue);
                assert.equal(vm.settings.defaultBucketLocationMessage, s3ViewModelSettings.defaultBucketLocationMessage);
                done();
            });
        });
    });
    describe('#fetchFromServer', () => {
        new APITestCases(
            function(tc) {
                var expected = tc.expected;
                describe('Case: ' + tc.description, () => {
                    before(tc.before);
                    after(tc.after);
                    it('fetches data from the server and updates its state', (done) => {
                        var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
                        vm.updateFromData()
                            .always(function() {
                                // VM is updated with data from the fake server
                                // observables
                                assert.equal(vm.ownerName(), expected.ownerName);
                                assert.equal(vm.nodeHasAuth(), expected.nodeHasAuth);
                                assert.equal(vm.userHasAuth(), expected.userHasAuth);
                                assert.equal(vm.currentBucket(), (expected.bucket === null) ? null : '');
                                assert.deepEqual(vm.urls(), expected.urls);
                                done();
                            });
                    });
                    describe('... and after updating computed values work as expected', () => {
                        it('shows settings if Node has auth and credentials are valid', (done) => {
                            var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showSettings(), expected.showSettings);
                                    done();
                                });
                        });
                        it('disables settings in User dosen\'t have auth and is not auth owner', (done) => {
                            var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.disableSettings(), expected.disableSettings);
                                    done();
                                });
                        });
                        it('shows the new bucket button if User has auth and is auth owner', (done) => {
                            var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showNewBucket(), expected.showNewBucket);
                                    done();
                                });
                        });
                        it('shows the import auth link if User has auth and Node is unauthorized', (done) => {
                            var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showImport(), expected.showImportAuth);
                                    done();
                                });
                        });
                        it('shows the create credentials link if User is unauthorized and Node is unauthorized ', (done) => {
                            var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.showCreateCredentials(), expected.showCreateCredentials);
                                    done();
                                });
                        });
                        it('lets User see change bucket UI if they are auth owner and Node has auth', (done) => {
                            var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
                            vm.updateFromData()
                                .always(function() {
                                    assert.equal(vm.canChange(), expected.canChange);
                                    done();
                                });
                        });
                        it('allows User to change buckets if there are buckets to be seleted and buckets are not currently being loaded ', (done) => {
                            var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
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
                    nodeHasAuth: false,
                    userHasAuth: false,
                    userIsOwner: false,
                    ownerName: null,
                    bucket: null,
                    validCredentials: false
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
                    nodeHasAuth: true,
                    userHasAuth: false,
                    userIsOwner: false,
                    ownerName: faker.name.findName(),
                    bucket: null,
                    validCredentials: true
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
                    nodeHasAuth: false,
                    userHasAuth: true,
                    userIsOwner: true,
                    ownerName: faker.name.findName(),
                    bucket: null,
                    validCredentials: true
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
                    nodeHasAuth: true,
                    userHasAuth: true,
                    userIsOwner: true,
                    ownerName: faker.name.findName(),
                    bucket: null,
                    validCredentials: true
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
            var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
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
                        spy.restore();
                        done();
                    });
                });
        });
    });
    describe('#selectBucket', () => {
        var putEndpoint = makeSettingsEndpoint();
        putEndpoint.method = 'PUT';
        putEndpoint.response = putEndpoint.response.result;
        // Bucket names cannot include periods
        var bucket = 'validbucket';
        putEndpoint.response.bucket = bucket;
        putEndpoint.response.hasBucket = true;
        var endpoints = [
            putEndpoint,
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
            var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });

            vm.updateFromData()
                .always(function() {
                    vm.selectedBucket(bucket);
                    var promise = vm.selectBucket();
                    promise.always(function() {
                        assert.equal(vm.currentBucket(), bucket, 'currentBucket not equal to ' + bucket);
                        done();
                    });
                });
        });
        it('alerts the user that the S3 addon does not support bucket names containing periods', (done) => {
            var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/'});
            var spy = sinon.spy(bootbox, 'alert');
            vm.updateFromData()
                .always(function () {
                    vm.selectedBucket('pew.pew.pew');
                    vm.selectBucket();
                    assert(spy.calledOnce);
                    spy.restore();
                    done();
                });
        });
    });
    describe('Authorization/Authentication: ', () => {
        var deleteEndpoint = makeSettingsEndpoint({
            nodeHasAuth: false,
            userHasAuth: true,
            userIsOwner: false,
            validCredentials: false
        });
        deleteEndpoint.method = 'DELETE';
        deleteEndpoint.response = deleteEndpoint.response.result;
        var importEndpoint = makeSettingsEndpoint({
            nodeHasAuth: true,
            userHasAuth: true,
            userIsOwner: true,
            validCredentials: true
        });
        importEndpoint.method = 'PUT';
        importEndpoint.url = URLS.import_auth;
        importEndpoint.response = importEndpoint.response.result;
        var createEndpoint = makeSettingsEndpoint({
            nodeHasAuth: true,
            userHasAuth: true,
            userIsOwner: true,
            validCredentials: true
        });
        createEndpoint.method = 'POST';
        createEndpoint.url = URLS.create;
        createEndpoint.response = createEndpoint.response.result;
        var endpoints = [
            makeSettingsEndpoint({
                nodeHasAuth: true,
                userHasAuth: true,
                userIsOwner: true,
                validCredentials: true
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
                var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
                vm.updateFromData()
                    .always(function() {
                        var promise = vm._deauthorizeNodeConfirm();
                        promise.always(function() {
                            assert.equal(vm.userHasAuth(), expected.userHasAuth);
                            assert.equal(vm.nodeHasAuth(), expected.nodeHasAuth);
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
                endpoints[0].response.result.nodeHasAuth = false;
                endpoints[0].response.result.validCredentials = false;

            });
            it('makes a PUT request to import auth and updates settings on success', (done) => {
                var expected = endpoints[2].response;
                var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
                vm.updateFromData()
                    .always(function() {
                        var promise = vm._importAuthConfirm();
                        promise.always(function() {
                            assert.equal(vm.nodeHasAuth(), expected.nodeHasAuth);
                            assert.isTrue(vm.showSettings());
                            done();
                        });
                    });
            });
        });
        describe('#createCredentials', () => {
            before(() => {
                // Prepare settings endpoint for next test
                endpoints[0].response.result.nodeHasAuth = false;
                endpoints[0].response.result.userHasAuth = false;
                // temporarily disable mock server autoRespond
                server.autoRespond = false;
            });
            after(() => {
                // restore fake server autoRespond
                server.autoRespond = true;
            });
            var expected = endpoints[0].response;
            it('makes a POST request to create auth and updates settings on success', (done) => {
                var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
                vm.updateFromData()
                    .always(function() {
                        var promise = vm.sendAuth();
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
            var vm = new s3NodeConfigVM('', {url: '/api/v1/12345/s3/settings/' });
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

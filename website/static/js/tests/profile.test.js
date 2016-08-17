/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var faker = require('faker');

var utils = require('./utils');
var profile = require('../profile');

// If this gets changed, website/static/urlValidatorTest.json also needs to match
// TODO auto load and parse website/static/urlValidatorTest.json as urlData
var urlData = {
  'testsPositive': {
    'definitelyawebsite.com':'should accept simple valid website',
    'https://Definitelyawebsite.com':'should accept valid website with protocol',
    'http://foo.com/blah_blah':'should accept valid website with path',
    'http://foo.com/blah_blah:5000/pathhere':'should accept valid website with port and path',
    'http://foo.com/blah_blah_(wikipedia)':'should accept valid website with parentheses in path',
    'http://userid@example.com/':'should accept valid user website',
    'http://userid@example.com:8080':'should accept valid user website with port',
    'http://userid:password@example.com/':'should accept valid user website with password',
    'http://userid:password@example.com:8080/':'should accept valid user and password website with path',
    'http://142.42.1.1':'should accept valid ipv4 website test 1',
    'http://10.1.1.0':'should accept valid ipv4 website test 2',
    'http://10.1.1.255':'should accept valid ipv4 website test 3',
    'http://224.1.1.1':'should accept valid ipv4 website test 4',
    'http://142.42.1.1:8080/':'should accept valid ipv4 website with port',
    'http://Bücher.de':'should accept valid website with unicode in domain',
    'http://heynow.ws/䨹':'should accept valid website with unicode in path',
    'http://localhost:5000/meetings':'should accept valid localhost website',
    'http://⌘.ws':'should accept valid website with only unicode in path',
    'http://⌘.ws/':'should accept valid website with only unicode in path and a / after domain',
    'http://foo.com/blah_(wikipedia)#cite-1':'should accept valid website with hashtag following parentheses in path',
    'http://foo.com/blah_(wikipedia)_blah#cite-1':'should accept valid website with hashtag in path',
    'http://foo.com/unicode_(✪)_in_parens':'should accept valid website with unicode in parentheses in path',
    'http://foo.com/(something)?after=parens':'should accept valid website with something after path',
    'http://staging.damowmow.com/':'should accept valid website with sub-domain',
    'http://☺.damowmow.com/':'should accept valid website with unicode in sub-domain',
    'http://code.google.com/events/#&product=browser':'should accept valid website with variables',
    'ftp://foo.bar/baz':'should acccept valid website with ftps',
    'http://foo.bar/?q=Test%20URL-encoded%20stuff':'should accept valid website with encoded stuff in path',
    'http://مثال.إختبار':'should accept valid unicode heavy website test 1',
    'http://例子.测试':'should accept valid unicode heavy website test 2',
    'http://उदाहरण.परीक्षा':'should accept valid unicode heavy website test 3',
    'http://-.~_!$&()*+,;=:%40:80%2f::::::@example.com':'should accept valid website with user but crazy username',
    'http://1337.net':'should accept valid website with just numbers in domain',
    'definitelyawebsite.com?real=yes&page=definitely':'should accept valid website with query',
    'http://a.b-c.de':'should accept valid website with dash'
  },
  'testsNegative': {
    'notevenclose': 'should deny simple invalid website',
    'http://': 'should deny invalid website with only http://',
    'http://.': 'should deny invalid website with only http://.',
    'http://..': 'should deny invalid website with only http://..',
    'http://../': 'should deny invalid website with only http://../',
    'http://?': 'should deny invalid website with only http://?',
    'http://??': 'should deny invalid website with only http://??',
    'http://??/': 'should deny invalid website with only http://??/',
    'http://#': 'should deny invalid website with only http://#',
    'http://##': 'should deny invalid website with only http://##',
    'http://##/': 'should deny invalid website with only http://##/',
    'http://foo.bar?q=Spaces should be encoded': 'should deny invalid website with spaces in path',
    '//': 'should deny invalid website with only //',
    '//a': 'should deny invalid website with only //a',
    '///a': 'should deny invalid website with only ///a',
    '///': 'should deny invalid website with only ///',
    'http:///a': 'should deny invalid website with three / in protocol',
    'rdar://1234': 'should deny invalid website with invalid protocol',
    'h://test': 'should deny invalid website with missing letters from protocol',
    'http:// shouldfail.com': 'should deny invalid website with space in beginning of domain',
    'http://should fail': 'should deny invalid website with space in middle of domain',
    'http://-error-.invalid/': 'should deny invalid website with dash at beginning and end of domain',
    'http://1.1.1.1.1': 'should deny invalid ipv4 website with 5 numbers',
    'http://567.100.100.100': 'should deny invalid ipv4 website with a number out of range',
    'http://-a.b.co': 'should deny invalid website with dash at beginning of sub-domain',
    'http://.www.foo.bar/': 'should deny invalid website with dot before sub-domain',
    'http://www.foo.bar./': 'should deny invalid website with dot after top-level-domain'
  }
}

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

describe('profile', () => {
    sinon.collection.restore();
    describe('ViewModels', () => {

        var nameURLs = {
            crud: '/settings/names/',
            impute: '/settings/names/impute/'
        };
        var server;

        var names = {
            full: faker.name.findName(),
            given: faker.name.firstName(),
            middle: [faker.name.lastName()],
            family: faker.name.lastName(),
            suffix: faker.name.suffix()
        };
        var imputedNames = {
            given: faker.name.firstName(),
            middle: [faker.name.lastName()],
            family: faker.name.lastName(),
            suffix: faker.name.suffix()
        };

        before(() => {
            // Set up fake server
            var endpoints = [
                {url: nameURLs.crud, response: names},
                {url: /\/settings\/names\/impute\/.+/, response: imputedNames}
            ];
            server = utils.createServer(sinon, endpoints);
        });

        after(() => {
            server.restore();
        });


        describe('NameViewModel', () => {
            var vm;

            // Constructor current sends a request, so need to make beforeEach async
            beforeEach((done) => {
                vm = new profile._NameViewModel(nameURLs, ['view', 'edit'], false, function() {
                    done();
                });
            });

            it('should fetch and update names upon instantiation', (done) => {
                var vm = new profile._NameViewModel(nameURLs, ['view', 'edit'], false, function() {
                    // Observables have been updated
                    assert.equal(this.full(), names.full);
                    assert.equal(this.given(), names.given);
                    assert.equal(this.family(), names.family);
                    assert.equal(this.suffix(), names.suffix);
                    done();
                });
            });

            it('should not crash initials function when name contains two spaces', () => {
                var initials = vm.initials('John  Quincy');
                assert.equal(initials, 'J. Q.');
            });

            describe('impute', () => {
                it('should send request and update imputed names', (done) => {
                    vm.impute().done(() => {
                        assert.equal(vm.given(), imputedNames.given);
                        done();
                    });
                });
            });

        describe('SocialViewModel', () => {
            var vm;
            var changeMessageSpy;
            beforeEach(() => {
                vm = new profile.SocialViewModel(nameURLs, ['view', 'edit']) ;
                changeMessageSpy = new sinon.spy(vm, 'changeMessage');
            });

            it('inherit from BaseViewModel', () => {
               assert.instanceOf(vm, profile.BaseViewModel);
            });

            describe('hasValidWebsites', () => {
                for (var i in urlData[testsPositive])
                    it(urlData[testsPositive][i], () => {
                        vm.profileWebsites([i]) ;
                        assert.isTrue(vm.hasValidWebsites()) ;
                    });
                }
                for (var j in urlData[testsNegative]) {
                    it(urlData[testsNegative][j], () => {
                        vm.profileWebsites([j]) ;
                        assert.isFalse(vm.hasValidWebsites()) ;
                    });
                }
            });

            describe('submit', () => {
                it('error message for invalid website', () => {
                    vm.profileWebsites(['definitelynotawebsite']) ;
                    vm.submit();
                    assert.called(changeMessageSpy);
                    assert.equal(vm.message(), 'Please update your website') ;
                });
                it('no error message for valid website', () => {
                    vm.profileWebsites(['definitelyawebsite.com']) ;
                    vm.submit();
                    assert.notCalled(changeMessageSpy);
                });
            });

        });

            // TODO: Test citation computes
        });

    // TODO: Test other profile ViewModels
    });
});


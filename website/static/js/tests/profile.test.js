/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var faker = require('faker');

var utils = require('./utils');
var profile = require('../profile');

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
                it('should reject simple invalid website', () => {
                    vm.profileWebsites(['definitelynotawebsite']) ;
                    assert.isFalse(vm.hasValidWebsites()) ;
                });
                it('should accept simple valid website', () => {
                    vm.profileWebsites(['definitelyawebsite.com']) ;
                    assert.isTrue(vm.hasValidWebsites()) ;
                });
                it('should accept valid website with protocol', () => {
                    vm.profileWebsites(['https://definitelyawebsite.com']) ;
                    assert.isTrue(vm.hasValidWebsites()) ;
                });
                it('should accept valid IPv4 website', () => {
                    vm.profileWebsites(['127.0.0.1']) ;
                    assert.isTrue(vm.hasValidWebsites()) ;
                });
                it('should accept valid website with path', () => {
                    vm.profileWebsites(['definitelyawebsite.com/definitelyapage/']) ;
                    assert.isTrue(vm.hasValidWebsites()) ;
                });
                it('should accept valid website with port and path', () => {
                    vm.profileWebsites(['127.0.0.1:5000/hello/']) ;
                    assert.isTrue(vm.hasValidWebsites()) ;
                });
                it('should accept valid website with query strings', () => {
                    vm.profileWebsites(['definitelyawebsite.com?real=yes&page=definitely']) ;
                    assert.isTrue(vm.hasValidWebsites()) ;
                });
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


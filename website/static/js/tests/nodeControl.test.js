/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var assign = require('object-assign');
var $ = require('jquery');

var utils = require('./utils');
var nodeControl = require('../nodeControl');

var nodeData = {
    node: {
        id: '24601',
        api_url: '/api/v1/project/24601/',
        watched_count: 0,
        identifiers: {doi: null, ark: null}
    },
    parent_node: {id: ''},
    user: {}
};

describe('nodeControl', () => {
    describe('ViewModels', () => {
        describe('ProjectViewModel', () => {
            var server;
            var vm = new nodeControl._ProjectViewModel(nodeData);
            var endpoints = [
                {method: 'POST', url: vm.apiUrl + 'identifiers/', response: {doi: '24601', ark: '24601'}}
            ];
            before(() => {
                server = utils.createServer(sinon, endpoints);
            });
            after(() => {
                server.restore();
            });
            it('has no identifiers when identifiers are null', () => {
                var vm = new nodeControl._ProjectViewModel(nodeData);
                assert.equal(vm.doi(), null);
                assert.equal(vm.ark(), null);
                assert.isFalse(vm.hasIdentifiers());
            });
            it('has identifiers when identifiers are not null', () => {
                var vm = new nodeControl._ProjectViewModel(nodeData);
                vm.doi('24601');
                vm.ark('24601');
                assert.isTrue(vm.hasIdentifiers());
            });
            it('can have identifiers when public, registered, and parent', () => {
                var data = assign({}, nodeData);
                data.node = assign(data.node, {is_registration: true, is_public: true});
                var vm = new nodeControl._ProjectViewModel(data);
                assert.isTrue(vm.canHaveIdentifiers);
            });
            it('cannot have identifiers when private, not registered, or not parent', () => {
                var vm;
                var data = assign({}, nodeData);
                data.node = assign(data.node, {is_registration: true, is_public: false});
                vm = new nodeControl._ProjectViewModel(data);
                assert.isFalse(vm.canHaveIdentifiers);
                data.node = assign(data.node, {is_registration: false, is_public: true});
                vm = new nodeControl._ProjectViewModel(data);
                assert.isFalse(vm.canHaveIdentifiers);
                data = assign(data, {parent_node: {id: '24602'}});
                data.node = assign(data.node, {is_registration: true, is_public: true});
                vm = new nodeControl._ProjectViewModel(data);
                assert.isFalse(vm.canHaveIdentifiers);
            });
            it('builds the correct absolute urls', () => {
                var vm = new nodeControl._ProjectViewModel(nodeData);
                vm.doi('24601');
                vm.ark('24601');
                assert.equal(vm.doiUrl(), 'http://ezid.cdlib.org/id/doi:24601');
                assert.equal(vm.arkUrl(), 'http://ezid.cdlib.org/id/ark:24601');
            });
            it('creates new identifiers', (done) => {
                vm.createIdentifiers().done(() => {
                    assert.equal(vm.doi(), '24601');
                    assert.equal(vm.ark(), '24601');
                    done();
                });
            });
        });
    });
});

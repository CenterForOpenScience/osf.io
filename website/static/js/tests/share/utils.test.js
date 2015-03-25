/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';

var assert = require('chai').assert;
var $osf = require('js/osfHelpers');

var utils = require('js/share/utils');
var testUtils = require('tests/utils');

var noop = function(){};

var resultsLoadingSpy = new sinon.spy();
describe('share/utils', () => {
    var query = '';
    var sort = 'sort';

    var vm = {
        page: 0,
        sort: function(){
            return sort;
        },
        sortMap: {
            sort: 'sort'
        },
        resultsLoading: resultsLoadingSpy,
        query: function(){return query;},
        optionalFilters: [],
        requiredFilters: []
    };

    describe('#loadMore', () => {
        var server;
        var stub;

        var emptyResponse = {
            count: 0,
            time: 0,
            results: []
        };

        var endpoints = [{
            method: 'GET',
            url: /\/api\/v1\/share\/.*/,
            response: emptyResponse
        }];

        before(() => {
            query = '';

            server = testUtils.createServer(sinon, endpoints);
            stub = sinon.stub(utils, 'buildQuery', function(){
                return query;
            });
        });
        after(() => {
            utils.buildQuery.restore();
            server.restore();
        });

        it('returns a promise that resolves to null when buildQuery returns an empty query', (done) => {
            utils.loadMore(vm)
                .then(function(data){
                    assert.isNull(data);
                    done();
                });
        });

        it('returns a promise that resolves to new data when called with a query', (done) => {
            query = 'q=toast';
            utils.loadMore(vm)
                .then(function(data){
                    assert.deepEqual(data, emptyResponse);
                    done();
                });
        });
    });

    describe('#buildURLParams', () => {

        afterEach(() => {
            vm.optionalFilters = [];
            vm.requiredFilters = [];
            query = '';
            sort = 'sort';
        });

        it('build url parameters of the form ?q=&required=&optional&sort=', () => {
            query = '1';
            vm.requiredFilters.push('2');
            vm.optionalFilters.push('3');
            sort = '4';
            assert.deepEqual('q=1&required=2&optional=3&sort=4', utils.buildURLParams(vm));
        });

        it('doesn\'t display parameters unless they have meaningful values', () => {
            query = '1';
            vm.requiredFilters.push('2');
            sort = '4';
            assert.deepEqual('q=1&required=2&sort=4', utils.buildURLParams(vm));

            vm.optionalFilters.push('3');
            vm.requiredFilters = [];
            assert.deepEqual('q=1&optional=3&sort=4', utils.buildURLParams(vm));

            vm.requiredFilters.push('2');
            sort = null;
            assert.deepEqual('q=1&required=2&optional=3', utils.buildURLParams(vm));

            sort = '4';
            query = null;
            assert.deepEqual('required=2&optional=3&sort=4', utils.buildURLParams(vm));

        });

    });
});

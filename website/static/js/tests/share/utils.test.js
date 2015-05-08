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

        it('builds url parameters of the form ?q=&required=&optional&sort=', () => {
            query = '1';
            vm.requiredFilters.push('2');
            vm.optionalFilters.push('3');
            sort = '4';
            assert.equal('q=1&required=2&optional=3&sort=4', utils.buildURLParams(vm));
        });

        it('doesn\'t display parameters unless they have meaningful values', () => {
            query = '1';
            vm.requiredFilters.push('2');
            sort = '4';
            assert.equal('q=1&required=2&sort=4', utils.buildURLParams(vm));

            vm.optionalFilters.push('3');
            vm.requiredFilters = [];
            assert.equal('q=1&optional=3&sort=4', utils.buildURLParams(vm));

            vm.requiredFilters.push('2');
            sort = null;
            assert.equal('q=1&required=2&optional=3', utils.buildURLParams(vm));

            sort = '4';
            query = null;
            assert.equal('required=2&optional=3&sort=4', utils.buildURLParams(vm));

        });
    });

    describe('#buildQuery', () => {
        before(() => {
            query = 'toast';
        });
        after(() => {
            query = '';
        });
        afterEach(() => {
            vm.optionalFilters = [];
            vm.requiredFilters = [];
        });


        it('makes a query like query AND (optional) AND (required)', () => {
            vm.optionalFilters.push('1');
            vm.requiredFilters.push('2');

            assert.equal('toast AND (1) AND (2)', utils.buildQuery(vm));
        });

        it('doesn\'t create invalid queries with empty filters', () => {
            vm.optionalFilters.push('1');
            assert.equal('toast AND (1)', utils.buildQuery(vm));

            vm.optionalFilters = [];
            vm.requiredFilters.push('2');
            assert.equal('toast AND (2)', utils.buildQuery(vm));
        });
    });


    describe('#updateFilter', () => {
        var stub;

        before(() => {
            stub = sinon.stub(utils, 'search', function(){});
        });

        after(() => {
            utils.search.restore();
            vm.requiredFilters = [];
            vm.optionalFilters = [];
        });

        it('adds filters to the optionalFilters unless it is already there or it is required', () => {
            utils.updateFilter(vm, 'test');
            assert.deepEqual(['test'], vm.optionalFilters);

            utils.updateFilter(vm, 'test');
            assert.deepEqual(['test'], vm.optionalFilters);

            utils.updateFilter(vm, 'test', true);
            assert.deepEqual(['test'], vm.optionalFilters);
        });

        it('adds filters to the required filters only if required is true and the filter is not already there', () => {
            utils.updateFilter(vm, 'test', true);
            assert.deepEqual(['test'], vm.requiredFilters);

            utils.updateFilter(vm, 'test', true);
            assert.deepEqual(['test'], vm.requiredFilters);

            utils.updateFilter(vm, 'toast');
            assert.deepEqual(['test'], vm.requiredFilters);
        });

    });

    describe('#removeFilter', () => {
        var stub;

        before(() => {
            stub = sinon.stub(utils, 'search', function(){});
        });

        after(() => {
            utils.search.restore();
        });

        it('removes filters from optional and required', () => {
            utils.updateFilter(vm, 'test');
            utils.updateFilter(vm, 'test', true);
            assert.deepEqual(['test'], vm.optionalFilters);
            assert.deepEqual(['test'], vm.requiredFilters);

            utils.removeFilter(vm, 'test');
            assert.deepEqual([], vm.optionalFilters);
            assert.deepEqual([], vm.requiredFilters);
            utils.removeFilter(vm, 'test');
            assert.deepEqual([], vm.optionalFilters);
            assert.deepEqual([], vm.requiredFilters);
        });

    });
});

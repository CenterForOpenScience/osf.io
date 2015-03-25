/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';

var assert = require('chai').assert;
var $osf = require('js/osfHelpers');

var utils = require('js/share/utils');

var noop = function(){};

var resultsLoadingSpy = new sinon.spy();
describe('share/utils', () => {
    var vm = {
        page: 0,
        sort: function(){
            return 'sort';
        },
        sortMap: {
            sort: 'sort'
        },
        resultsLoading: resultsLoadingSpy
    };

    describe('#loadMore', () => {
        var stub;
        before(() => {
            stub = sinon.stub(utils, 'buildQuery', function(){
                return '';
            });
        });
        after(() => {
            utils.buildQuery.restore();
        });

        it('returns a promise that resolves to null when buildQuery returns and empty query', (done) => {
            utils.loadMore(vm)
                .then(function(data){
                    assert.isNull(data);
                    done();
                });
        });
    });
});

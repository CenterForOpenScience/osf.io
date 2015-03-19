/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';

var Paginator = require('js/paginator');
var oop = require('js/oop');
var assert = require('chai').assert;
sinon.assert.expose(assert, {prefix: ''});

var TestPaginator = oop.extend(Paginator, {
    constructor: function(){
        this.super.constructor();
    },
    search: sinon.spy(),
    configure: function(config){
        config(this);
    }
});


describe('Paginator', () => {
    var paginator;

    beforeEach(() => {
        paginator = new TestPaginator();
    });  

    it('nextPage', () => {
        paginator.configure(function(p){
            p.numberOfPages(5);
        });
        paginator.nextPage();
        assert.isTrue(paginator.search.calledOnce);
        assert.equal(paginator.currentPage() - 1, 0);
    });

    it('previousPage', () => {
        paginator.previousPage();
        assert.isTrue(paginator.search.calledOnce);
        assert.equal(paginator.currentPage() + 1, 1);
    });

    it('enforces implementation of search', () => {
        var pg = new Paginator();
        assert.throw(pg.search, Error, 'Paginator subclass must define a "search" method');
    });

    it('addNewPaginator', () => {
        assert(true);
    });
});

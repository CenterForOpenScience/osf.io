/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';

var Paginator = require('js/paginator');
var oop = require('js/oop');
var assert = require('chai').assert;
sinon.assert.expose(assert, {prefix: ''});

var spy = new sinon.spy();

var TestPaginator = oop.extend(Paginator, {
    constructor: function(){
        this.super.constructor();
    },
    fetchResults: spy,
    configure: function(config){
        config(this);
    }
});


describe('Paginator', () => {
    var paginator;
    var numberOfPages;
    var currentPage;
    var pageToGet;

    beforeEach(() => {
        paginator = new TestPaginator();
    });

    afterEach(() => {
        spy.reset();
        numberOfPages = 0;
        currentPage = 0;
        pageToGet = 0;
    });

    it('previousPage', () => {
        numberOfPages = 5;
        currentPage = 3;
        paginator.configure(function(p){
            p.numberOfPages(numberOfPages);
            p.currentPage(currentPage);
        });
        paginator.previousPage();
        assert.calledOnce(paginator.fetchResults);
        assert.equal(paginator.pageToGet() + 1, currentPage);
    });

    it('previousPage doesnot fetchResult when pageNum is 0', () => {
        numberOfPages = 5;
        currentPage = 0;
        paginator.configure(function(p){
            p.numberOfPages(numberOfPages);
            p.currentPage(currentPage);
        });
        paginator.previousPage();
        assert.isFalse(paginator.fetchResults.called);
        assert.equal(paginator.pageToGet() + 1, currentPage);
    });

    it('nextPage', () => {
        numberOfPages = 5;
        paginator.configure(function(p){
            p.numberOfPages(numberOfPages);
        });
        paginator.nextPage();
        assert.calledOnce(paginator.fetchResults);
        assert.equal(paginator.pageToGet() - 1, currentPage);
    });

    it('nextPage doesnot fetchResult when pageNum is at the end', () => {
        numberOfPages = 5;
        currentPage = 4;
        paginator.configure(function(p){
            p.numberOfPages(numberOfPages);
            p.currentPage(currentPage);
        });
        paginator.nextPage();
        assert.isFalse(paginator.fetchResults.called);
        assert.equal(paginator.pageToGet() - 1, currentPage);
    });

    it('enforces implementation of fetchResults', () => {
        var pg = new Paginator();
        assert.throw(pg.fetchResults, Error, 'Paginator subclass must define a "fetchResults" method');
    });

    describe('addNewPaginator', () => {
        var maxPaginatorNumber = 9;

        it('one page no paginator', () => {
            numberOfPages = 1;
            paginator.configure(function(p){
                p.numberOfPages(numberOfPages);
            });
            paginator.addNewPaginators();
            assert.equal(paginator.paginators().length, 0);
        });

        it('less than 7 pages', () => {
            numberOfPages = 6;
            paginator.configure(function(p){
                p.numberOfPages(numberOfPages);
            });
            paginator.addNewPaginators();
            assert.equal(paginator.paginators().length, numberOfPages + 2);
            assert.equal(paginator.paginators()[0].text, '&lt;');
            assert.equal(paginator.paginators()[1].text, 1);
            assert.equal(
                paginator.paginators()[paginator.paginators().length - 1].text,
                '&gt;'
            );
            assert.equal(
                paginator.paginators()[paginator.paginators().length - 2].text,
                numberOfPages
            );
        });

        it('more than 7 pages, currentPage less than 4, one ellipse at the end', () => {
            numberOfPages = 9;
            currentPage = 3;
            paginator.configure(function(p){
                p.numberOfPages(numberOfPages);
                p.currentPage(currentPage);
            });
            paginator.addNewPaginators();
            assert.equal(paginator.paginators().length, maxPaginatorNumber);
            assert.equal(paginator.paginators()[0].text, '&lt;');
            assert.equal(paginator.paginators()[maxPaginatorNumber - 1].text, '&gt;');
            assert.equal(paginator.paginators()[maxPaginatorNumber - 2].text, numberOfPages);
            assert.equal(paginator.paginators()[maxPaginatorNumber - 3].text, '...');
        });

        it('more than 7 pages, currentPage more than numbersOfPages - 5, one ellipse at the beginning',
            () => {
            numberOfPages = 9;
            currentPage = 5;
            paginator.configure(function(p){
                p.numberOfPages(numberOfPages);
                p.currentPage(currentPage);
            });
            paginator.addNewPaginators();
            assert.equal(paginator.paginators().length, maxPaginatorNumber);
            assert.equal(paginator.paginators()[0].text, '&lt;');
            assert.equal(paginator.paginators()[1].text, 1);
            assert.equal(paginator.paginators()[2].text, '...');
            assert.equal(paginator.paginators()[maxPaginatorNumber - 1].text, '&gt;');
            assert.equal(paginator.paginators()[maxPaginatorNumber - 2].text, numberOfPages);

        });

        it('more than 7 pages, currentPage more than 5 and numbersOfPages - 5, two ellipses',
            () => {
            numberOfPages = 9;
            currentPage = 4;
            paginator.configure(function(p){
                p.numberOfPages(numberOfPages);
                p.currentPage(currentPage);
            });
            paginator.addNewPaginators();
            assert.equal(paginator.paginators().length, maxPaginatorNumber);
            assert.equal(paginator.paginators()[0].text, '&lt;');
            assert.equal(paginator.paginators()[1].text, 1);
            assert.equal(paginator.paginators()[2].text, '...');
            assert.equal(paginator.paginators()[maxPaginatorNumber - 1].text, '&gt;');
            assert.equal(paginator.paginators()[maxPaginatorNumber - 2].text, numberOfPages);
            assert.equal(paginator.paginators()[maxPaginatorNumber - 3].text, '...');

        });

    });
});

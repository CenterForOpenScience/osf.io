'use strict';

var $ = require('jquery');
var ko = require('knockout');

var osfHelpers = require('osfHelpers');
var Paginator = require('js/paginator');
var oop = require('js/oop');

describe('paginator', () => {

    var numberofPages = function(){
        return 5;
    };

    var currentPage = function(){
        return 1;
    };

    var paginators = function(){
        return [];
    };

    it('nextPage', () => {
        var newCurrentPage = Paginator.nextPage();
        assert.equal(newCurrentPage, currentPage + 1);
    });

    it('previousPage', () => {
        var newCurrentPage = Paginator.previousPage();
        assert.equal(newCurrentPage, currentPage - 1);
    });

    it('search', () => {
        var error = Paginator.previousPage();
        assert.equal(error, 'Paginator subclass must define a "search" method.');
    });

    it('addNewPaginator', () => {
        var newPaginator = Paginator.addNewPaginators();
        assert.equal(paginators.length(), 1);
    });
});
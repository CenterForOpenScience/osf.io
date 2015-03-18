'use strict';

var $ = require('jquery');
var ko = require('knockout');

var osfHelpers = require('osfHelpers');
var Paginator = require('js/paginator');
var oop = require('js/oop');
var assert = require('chai').assert;

describe('Paginator', () => {
    var vm;
    var numberOfPage = 5;
    var currentPage = 1;
    var paginators = [];

    beforeEach(() => {
        vm = new Paginator;
    });

    it('nextPage', () => {
        var newCurrentPage = vm.nextPage();
        assert.equal(newCurrentPage, currentPage + 1);
    });

    it('previousPage', () => {
        var newCurrentPage = vm.previousPage();
        assert.equal(newCurrentPage, currentPage - 1);
    });

    it('search', () => {
        assert.throw(vm.previousPage(), 'Paginator subclass must define a "search" method.');
    });

    it('addNewPaginator', () => {
        var newPaginator = vm.addNewPaginators();
        assert.equal(paginators.length(), 1);
    });
});
'use strict';

var $ = require('jquery');
var ko = require('knockout');

var osfHelpers = require('osfHelpers');
var Paginator = require('js/paginator');
var oop = require('js/oop');
var assert = require('chai').assert;
sinon.assert.expose(assert, {prefix: ''});


describe('Paginator', () => {
    var vm;
    //var numberOfPage = 5;
    //var currentPage = 1;
    //var paginators = [];

    beforeEach(() => {
        vm = oop.extend(Paginator, {
            constructor(){
                var self = this;
                self.numberOfPage = 5;
                self.currentPage = 1;
                self.paginators = [];
            },
            search(){
                return True;
            }
        });
    });


    it('nextPage', () => {
        var newCurrentPage = vm.nextPage();
        assert.equal(newCurrentPage, vm.currentPage + 1);
    });

    it('previousPage', () => {
        var newCurrentPage = vm.previousPage();
        assert.equal(newCurrentPage, vm.currentPage - 1);
    });

    it('search', () => {
        assert.throw(vm.previousPage(), 'Paginator subclass must define a "search" method.');
    });

    it('addNewPaginator', () => {
        var newPaginator = vm.addNewPaginators();
        assert.equal(vm.paginators.length(), 1);
    });
});
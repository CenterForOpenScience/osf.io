'use strict';

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
        var ins = new vm;
        var newCurrentPage = ins.nextPage();
        assert.true(newCurrentPage);
        assert.equal(ins.currentPage() - 1, 1);
    });

    it('previousPage', () => {
        var ins = new vm;
        var newCurrentPage = ins.previousPage();
        assert.true(newCurrentPage);
        assert.equal(ins.currentPage() + 1, 1);
    });

    it('search', () => {
        var ins = new vm
        assert.equal(true, ins.search());
    });

    it('addNewPaginator', () => {
        var ins = new vm;
        var newPaginator = ins.addNewPaginators();
        assert.equal(ins.paginators.length(), 1);
    });
});
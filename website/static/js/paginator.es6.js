/**
 * Paginator model
 */
'use strict';
var ko = require('knockout');
var oop = require('js/oop');
var MAX_PAGES_ON_PAGINATOR = 7;
var MAX_PAGES_ON_PAGINATOR_SIDE = 5;

var Paginator = oop.defclass({
    constructor() {
        this.numberOfPages = ko.observable(0);
        this.currentPage = ko.observable(0);
        this.paginators = ko.observableArray([]);
    },
    addNewPaginators() {
        var self = this;
        self.paginators.removeAll();
        if (self.numberOfPages() > 1) {
            self.paginators.push({
                style: (self.currentPage() === 0) ? 'disabled' : '',
                handler: self.previousPage.bind(self),
                text: '&lt;'
            });
            self.paginators.push({
                style: (self.currentPage() === 0) ? 'active' : '',
                text: '1',
                handler: function() {
                    self.currentPage(0);
                    self.search();
                }
            });
            if (self.numberOfPages() <= MAX_PAGES_ON_PAGINATOR) {
                for (var i = 1; i < self.numberOfPages() - 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.currentPage(parseInt(this.text) - 1);
                            self.search();
                        }
                    });
                }
            } else if (self.currentPage() < MAX_PAGES_ON_PAGINATOR_SIDE - 1) { // One ellipse at the end
                for (var i = 1; i < MAX_PAGES_ON_PAGINATOR_SIDE; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.currentPage(parseInt(this.text) - 1);
                            self.search();
                        }
                    });
                }
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
            } else if (self.currentPage() > self.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE) { // one ellipses at the beginning
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
                for (var i = self.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE; i < self.numberOfPages() - 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.currentPage(parseInt(this.text) - 1);
                            self.search();
                        }
                    });
                }
            } else { // two ellipses
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
                for (var i = self.currentPage() - 1; i <= self.currentPage() + 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.currentPage(parseInt(this.text) - 1);
                            self.search();
                        }
                    });
                }
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
            }
            self.paginators.push({
                style: (self.currentPage() === self.numberOfPages() - 1) ? 'active' : '',
                text: self.numberOfPages(),
                handler: function() {
                    self.currentPage(self.numberOfPages() - 1);
                    self.search();
                }
            });
            self.paginators.push({
                style: (self.currentPage() === self.numberOfPages() - 1) ? 'disabled' : '',
                handler: self.nextPage.bind(self),
                text: '&gt;'
            });
        }
    },
    nextPage(){
        this.currentPage(this.currentPage() + 1);
        this.search();
    },
    previousPage(){
        this.currentPage(this.currentPage() - 1);
        this.search();
    },
    search() {
        throw new Error('Paginator subclass must define a "search" method.');
    }
});
module.exports = Paginator;

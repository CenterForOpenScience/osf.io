/**
 * Paginator model
 */
'use strict';
var ko = require('knockout');
var oop = require('js/oop');
var MAX_PAGES_ON_PAGINATOR = 7;
var MAX_PAGES_ON_PAGINATOR_SIDE = 5;




var Paginator = oop.defclass({
    constructor: function() {
        this.pageToGet = ko.observable(0);
        this.numberOfPages = ko.observable(0);
        this.currentPage = ko.observable(0);
        this.paginators = ko.observableArray([]);
    },
    addNewPaginators: function() {
        var self = this;
        var i;
        self.paginators.removeAll();
        if (self.numberOfPages() > 1) {
            self.paginators.push({
                style: (self.currentPage() === 0) ? 'disabled' : '',
                handler: self.previousPage.bind(self),
                text: '&lt;'
            }); /* jshint ignore:line */
                /* functions defined inside loop */

            self.paginators.push({
                style: (self.currentPage() === 0) ? 'active' : '',
                text: '1',
                handler: function() {
                    self.pageToGet(0);
                    if (self.pageToGet() !== self.currentPage()) {
                        self.fetchResults();
                    }
                }
            });
            if (self.numberOfPages() <= MAX_PAGES_ON_PAGINATOR) {
                for (i = 1; i < self.numberOfPages() - 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.pageToGet(parseInt(this.text) - 1);
                            if (self.pageToGet() !== self.currentPage()) {
                                self.fetchResults();
                            }
                        }
                    });/* jshint ignore:line */
                    // function defined inside loop
                }
            } else if (self.currentPage() < MAX_PAGES_ON_PAGINATOR_SIDE - 1) { // One ellipse at the end
                for (i = 1; i < MAX_PAGES_ON_PAGINATOR_SIDE; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.pageToGet(parseInt(this.text) - 1);
                            if (self.pageToGet() !== self.currentPage()) {
                                self.fetchResults();
                            }
                        }
                    });/* jshint ignore:line */
                    // functions defined inside loop

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
                for (i = self.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE; i < self.numberOfPages() - 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.pageToGet(parseInt(this.text) - 1);
                            if (self.pageToGet() !== self.currentPage()) {
                                self.fetchResults();
                            }
                        }
                    });/* jshint ignore:line */
                    // function defined inside loop

                }
            } else { // two ellipses
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
                for (i = self.currentPage() - 1; i <= self.currentPage() + 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.pageToGet(parseInt(this.text) - 1);
                            if (self.pageToGet() !== self.currentPage()) {
                                self.fetchResults();
                            }
                        }
                    });/* jshint ignore:line */
                    // functions defined inside loop

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
                    self.pageToGet(self.numberOfPages() - 1);
                    if (self.pageToGet() !== self.currentPage()) {
                        self.fetchResults();
                    }
                }
            });
            self.paginators.push({
                style: (self.currentPage() === self.numberOfPages() - 1) ? 'disabled' : '',
                handler: self.nextPage.bind(self),
                text: '&gt;'
            });
        }
    },
    nextPage: function() {
        this.pageToGet(this.currentPage() + 1);
        if (this.pageToGet() < this.numberOfPages()){
            this.fetchResults();
        }
    },
    previousPage: function() {
        this.pageToGet(this.currentPage() - 1);
        if (this.pageToGet() >= 0) {
            this.fetchResults();
        }
    },
    fetchResults: function() {
        throw new Error('Paginator subclass must define a "fetchResults" method.');
    }
});


module.exports = Paginator;

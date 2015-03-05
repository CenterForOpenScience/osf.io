/**
* Controls the "Add Links" modal.
*/
'use strict';

var $ = require('jquery');
var ko = require('knockout');

var osfHelpers = require('osfHelpers');


// Grab nodeID from global context (mako)
var nodeApiUrl = window.contextVars.node.urls.api;
var nodeId = window.contextVars.node.id;

var AddPointerViewModel = function(nodeTitle) {

    var self = this;

    self.nodeTitle = nodeTitle;
    self.submitEnabled = ko.observable(true);

    self.query = ko.observable();
    self.results = ko.observableArray();
    self.selection = ko.observableArray();
    self.errorMsg = ko.observable('');
    self.numberOfPages = ko.observable(0);
    self.currentPage = ko.observable(0);
    self.totalPages = ko.observable(0);
    self.paginators = ko.observableArray([]);

    self.foundResults = ko.computed(function() {
        return self.query() && self.results().length;
    });

    self.noResults = ko.computed(function() {
        return self.query() && !self.results().length;
    });

    var MAX_PAGES_ON_PAGINATOR = 7;
    var MAX_PAGES_ON_PAGINATOR_SIDE = 5;

    self.addNewPaginators = function() {
        console.log("1");
        self.paginators.removeAll();
        if (self.numberOfPages() > 1) {
            self.paginators.push({
                style: (self.currentPage() === 0)? 'disabled' : '',
                handler: self.previousPage,
                text: '&lt;'
            });
            self.paginators.push({
                style: (self.currentPage() === 0)? 'active' : '',
                text: '1',
                handler: function () {
                    self.currentPage(0);
                    self.search();
                }
            });
            if (self.numberOfPages() <= MAX_PAGES_ON_PAGINATOR) {
                for (var i = 1; i < self.numberOfPages() - 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i)? 'active' : '',
                        text: i + 1,
                        handler: function () {
                            self.currentPage(parseInt(this.text) - 1);
                            self.search();
                        }
                    });
                }
            } else if (self.currentPage() < MAX_PAGES_ON_PAGINATOR_SIDE - 1) { // One ellipse at the end
                for (var i = 1; i < MAX_PAGES_ON_PAGINATOR_SIDE; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i)? 'active' : '',
                        text: i + 1,
                        handler: function () {
                            self.currentPage(parseInt(this.text) - 1);
                            self.search();
                        }
                    });
                }
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function () {}
                });
            } else if (self.currentPage() > self.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE) { // one ellipses at the beginning
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function () {}
                });
                for (var i = self.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE; i < self.numberOfPages() - 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i)? 'active' : '',
                        text: i + 1,
                        handler: function () {
                            self.currentPage(parseInt(this.text) - 1);
                            self.search();
                        }
                    });
                }
            } else { // two ellipses
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function () {}
                });
                for (var i = self.currentPage() - 1; i <= self.currentPage() + 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function () {
                            self.currentPage(parseInt(this.text) - 1);
                            self.search();
                        }
                    });
                }
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function () {}
                });
            }
            self.paginators.push({
                style: (self.currentPage() === self.numberOfPages() - 1)? 'active' : '',
                text: self.numberOfPages(),
                handler: function () {
                    self.currentPage(self.numberOfPages() - 1);
                    self.search();
                }
            });
            self.paginators.push({
                style: (self.currentPage() === self.numberOfPages() - 1)? 'disabled' : '',
                handler: self.nextPage,
                text: '&gt;'
            });
        }
    };

    self.nextPage = function() {
        self.currentPage(self.currentPage() + 1);
        self.search();
    };

    self.previousPage = function() {
        self.currentPage(self.currentPage() - 1);
        self.search();
    };

    self.search = function(includePublic) {
        self.errorMsg('');
        if (self.query()) {
            osfHelpers.postJSON(
                '/api/v1/search/node/',
                {
                    query: self.query(),
                    nodeId: nodeId,
                    includePublic: includePublic,
                    page: self.currentPage
                }
            ).done(function (result) {
                    if (!result.nodes.length) {
                        self.errorMsg('No results found.');
                    }
                    self.results(result.nodes);
                    self.currentPage(result.page);
                    self.numberOfPages(result.pages);
                    console.log(result.nodes);
                    console.log(result.page);
                    console.log(result.pages);
                    self.addNewPaginators();
                }).fail(
                osfHelpers.handleJSONError
            );
        } else{
            self.results([]);
            self.currentPage(0);
            self.totalPages(0);
        }
    };

    self.addTips = function(elements) {
        elements.forEach(function(element) {
            $(element).find('.contrib-button').tooltip();
        });
    };

    self.add = function(data) {
        self.selection.push(data);
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    };

    self.remove = function(data) {
        self.selection.splice(
            self.selection.indexOf(data), 1
        );
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    };

    self.addAll = function() {
        $.each(self.results(), function(idx, result) {
            if (self.selection().indexOf(result) === -1) {
                self.add(result);
            }
        });
    };

    self.removeAll = function() {
        $.each(self.selection(), function(idx, selected) {
            self.remove(selected);
        });
    };

    self.selected = function(data) {
        for (var idx=0; idx < self.selection().length; idx++) {
            if (data.id === self.selection()[idx].id) {
                return true;
            }
        }
        return false;
    };

    self.submit = function() {
        self.submitEnabled(false);
        var nodeIds = osfHelpers.mapByProperty(self.selection(), 'id');
        osfHelpers.postJSON(
            nodeApiUrl + 'pointer/',
            {nodeIds: nodeIds}
        ).done(function() {
            window.location.reload();
        }).fail(function(data) {
                self.submitEnabled(true);
                osfHelpers.handleJSONError(data);
            }
        );
    };

    self.clear = function() {
        self.query('');
        self.results([]);
        self.selection([]);
    };

    self.authorText = function(node) {
        var rv = node.firstAuthor;
        if (node.etal) {
            rv += ' et al.';
        }
        return rv;
    };

};


var LinksViewModel = function($elm) {

    var self = this;
    self.links = ko.observableArray([]);

    $elm.on('shown.bs.modal', function() {
        if (self.links().length === 0) {
            $.ajax({
                type: 'GET',
                url: nodeApiUrl + 'pointer/',
                dataType: 'json',
            }).done(function(response) {
                self.links(response.pointed);
            }).fail(function() {
                $elm.modal('hide');
                osfHelpers.growl('Error:','Could not get links');
            });
        }
    });

};

////////////////
// Public API //
////////////////

function PointerManager(selector, nodeName) {
    var self = this;
    self.selector = selector;
    self.$element = $(self.selector);
    self.nodeName = nodeName;
    self.viewModel = new AddPointerViewModel(nodeName);
    self.init();
}

PointerManager.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
    self.$element.on('hidden.bs.modal', function() {
        self.viewModel.clear();
    });
};

function PointerDisplay(selector) {
    this.selector = selector;
    this.$element = $(selector);
    this.viewModel = new LinksViewModel(this.$element);
    ko.applyBindings(this.viewModel, this.$element[0]);
}

module.exports = {
    PointerManager: PointerManager,
    PointerDisplay: PointerDisplay
};

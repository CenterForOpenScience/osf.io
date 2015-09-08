/**
 * Controls the "Add Links" modal.
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');

var osfHelpers = require('js/osfHelpers');
var Paginator = require('js/paginator');
var oop = require('js/oop');

// Grab nodeID from global context (mako)
var nodeApiUrl = window.contextVars.node.urls.api;
var nodeId = window.contextVars.node.id;

var SEARCH_ALL_SUBMIT_TEXT = 'Search all projects';
var SEARCH_MY_PROJECTS_SUBMIT_TEXT = 'Search my projects';

var AddPointerViewModel = oop.extend(Paginator, {
    constructor: function(nodeTitle) {
        this.super.constructor.call(this);
        var self = this;
        this.nodeTitle = nodeTitle;
        this.submitEnabled = ko.observable(true);
        this.searchAllProjectsSubmitText = ko.observable(SEARCH_ALL_SUBMIT_TEXT);
        this.searchMyProjectsSubmitText = ko.observable(SEARCH_MY_PROJECTS_SUBMIT_TEXT);

        this.query = ko.observable();
        this.results = ko.observableArray();
        this.selection = ko.observableArray();
        this.errorMsg = ko.observable('');
        this.totalPages = ko.observable(0);
        this.includePublic = ko.observable(true);
        this.searchWarningMsg = ko.observable('');
        this.submitWarningMsg = ko.observable('');
        this.loadingResults = ko.observable(false);

        this.foundResults = ko.pureComputed(function() {
            return self.query() && self.results().length;
        });

        this.noResults = ko.pureComputed(function() {
            return self.query() && !self.results().length;
        });
    },
    searchAllProjects: function() {
        this.includePublic(true);
        this.pageToGet(0);
        this.searchAllProjectsSubmitText('Searching...');
        this.fetchResults();
    },
    searchMyProjects: function() {
        this.includePublic(false);
        this.pageToGet(0);
        this.searchMyProjectsSubmitText('Searching...');
        this.fetchResults();
    },
    fetchResults: function() {
        var self = this;
        self.errorMsg('');
        self.searchWarningMsg('');

        if (self.query()) {
            self.results([]); // clears page for spinner
            self.loadingResults(true); // enables spinner

            osfHelpers.postJSON(
                '/api/v1/search/node/', {
                    query: self.query(),
                    nodeId: nodeId,
                    includePublic: self.includePublic(),
                    page: self.pageToGet()
                }
            ).done(function(result) {
                if (!result.nodes.length) {
                    self.errorMsg('No results found.');
                }
                self.results(result.nodes);
                self.currentPage(result.page);
                self.numberOfPages(result.pages);
                self.addNewPaginators();
            }).fail(function(xhr) {
                    self.searchWarningMsg(xhr.responseJSON && xhr.responseJSON.message_long);
            }).always( function (){
                self.searchAllProjectsSubmitText(SEARCH_ALL_SUBMIT_TEXT);
                self.searchMyProjectsSubmitText(SEARCH_MY_PROJECTS_SUBMIT_TEXT);
                self.loadingResults(false);
            });
        } else {
            self.results([]);
            self.currentPage(0);
            self.totalPages(0);
            self.searchAllProjectsSubmitText(SEARCH_ALL_SUBMIT_TEXT);
            self.searchMyProjectsSubmitText(SEARCH_MY_PROJECTS_SUBMIT_TEXT);
        }
    },
    addTips: function(elements) {
        elements.forEach(function(element) {
            $(element).find('.contrib-button').tooltip();
        });
    },
    add: function(data) {
        this.selection.push(data);
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    },
    remove: function(data) {
        var self = this;
        self.selection.splice(
            self.selection.indexOf(data), 1
        );
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    },
    addAll: function() {
        var self = this;
        $.each(self.results(), function(idx, result) {
            if (self.selection().indexOf(result) === -1) {
                self.add(result);
            }
        });
    },
    removeAll: function() {
        var self = this;
        $.each(self.selection(), function(idx, selected) {
            self.remove(selected);
        });
    },
    selected: function(data) {
        var self = this;
        for (var idx = 0; idx < self.selection().length; idx++) {
            if (data.id === self.selection()[idx].id) {
                return true;
            }
        }
        return false;
    },
    submit: function() {
        var self = this;
        self.submitEnabled(false);
        self.submitWarningMsg('');

        var nodeIds = osfHelpers.mapByProperty(self.selection(), 'id');

        osfHelpers.postJSON(
            nodeApiUrl + 'pointer/', {
                nodeIds: nodeIds
            }
        ).done(function() {
            window.location.reload();
        }).fail(function(data) {
            self.submitEnabled(true);
            self.submitWarningMsg(data.responseJSON && data.responseJSON.message_long);
        });
    },
    clear: function() {
        this.query('');
        this.results([]);
        this.selection([]);
        this.searchWarningMsg('');
        this.submitWarningMsg('');
    },
    authorText: function(node) {
        var rv = node.firstAuthor;
        if (node.etal) {
            rv += ' et al.';
        }
        return rv;
    }
});

var LinksViewModel = function($elm) {

    var self = this;
    self.links = ko.observableArray([]);

    $elm.on('shown.bs.modal', function() {
        if (self.links().length === 0) {
            $.ajax({
                type: 'GET',
                url: nodeApiUrl + 'pointer/',
                dataType: 'json'
            }).done(function(response) {
                self.links(response.pointed);
            }).fail(function() {
                $elm.modal('hide');
                osfHelpers.growl('Error:', 'Could not get links');
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

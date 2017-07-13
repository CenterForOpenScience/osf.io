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
var nodeLinksUrl = osfHelpers.apiV2Url('nodes/' + nodeId + '/node_links/', {});

var SEARCH_ALL_SUBMIT_TEXT = 'Search all projects';
var SEARCH_MY_PROJECTS_SUBMIT_TEXT = 'Search my projects';

var AddPointerViewModel = oop.extend(Paginator, {
    constructor: function(nodeTitle){
        var self = this;
        this.super.constructor.call(this);
        this.nodeTitle = nodeTitle;
        this.submitEnabled = ko.observable(true);
        this.searchAllProjectsSubmitText = ko.observable(SEARCH_ALL_SUBMIT_TEXT);
        this.searchMyProjectsSubmitText = ko.observable(SEARCH_MY_PROJECTS_SUBMIT_TEXT);
        this.query = ko.observable();
        this.results = ko.observableArray();
        this.selection = ko.observableArray();
        this.errorMsg = ko.observable('');
        this.totalPages = ko.observable(0);
        this.includePublic = ko.observable(false);
        this.dirty = ko.observable(false);
        this.searchWarningMsg = ko.observable('');
        this.submitWarningMsg = ko.observable('');
        this.loadingResults = ko.observable(false);
        this.inputType = ko.observable('nodes');
        this.foundResults = ko.pureComputed(function(){
            return self.results().length;
        });
        this.noResults = ko.pureComputed(function(){
            return self.query() && !self.results().length;
        });
        this.searchMyProjects();
    },
    doneSearching: function(){
        var self = this;
        self.searchAllProjectsSubmitText(SEARCH_ALL_SUBMIT_TEXT);
        self.searchMyProjectsSubmitText(SEARCH_MY_PROJECTS_SUBMIT_TEXT);
        self.loadingResults(false);
    },
    searchAllProjects: function(){
        var self = this;
        self.includePublic(true);
        self.pageToGet(0);
        self.searchAllProjectsSubmitText('Searching...');
        self.loadingResults(true);
        self.fetchResults();
    },
    searchMyProjects: function(){
        var self = this;
        self.includePublic(false);
        self.pageToGet(0);
        self.searchMyProjectsSubmitText('Searching...');
        self.loadingResults(true);
        self.fetchResults();
    },
    fetchResults: function(){
        var self = this;
        self.errorMsg('');
        self.searchWarningMsg('');
        self.results([]); // clears page for spinner
        self.selection([]);
        var pageNum = self.pageToGet() + 1;
        var userOrPublicNodes = self.includePublic() ? '' : 'users/me/';
        var url = osfHelpers.apiV2Url(
             userOrPublicNodes + self.inputType() + '/', {
              query : {
                'filter[title]' : self.query(),
                'page' : pageNum,
                'embed' : 'contributors',
                'page[size]' : '4'
              }
            }
        );
        var requestNodes = osfHelpers.ajaxJSON(
            'GET',
            url,
            {'isCors': true}
        );
        requestNodes.done(function(response){
            var nodes = response.data;
            var count = nodes.length;
            if (!count){
                self.errorMsg('No results found.');
                self.doneSearching();
                return;
            }
            var requestNodeLinks = osfHelpers.ajaxJSON(
                'GET',
                nodeLinksUrl,
                {'isCors': true}
            );
            requestNodeLinks.done(function(response){
                var embedNodeIds = [];
                for (var i = 0; i < response.data.length; i++){
                    embedNodeIds.push(response.data[i].embeds.target_node.data.id);
                }
                nodes.forEach(function(each){
                    if (each.type === 'registrations'){
                        each.dateRegistered = new osfHelpers.FormattableDate(each.attributes.date_registered);
                    } else {
                        each.dateCreated = new osfHelpers.FormattableDate(each.attributes.date_created);
                        each.dateModified = new osfHelpers.FormattableDate(each.attributes.date_modified);
                    }
                    if (embedNodeIds.indexOf(each.id) !== -1){
                        self.selection.push(each);
                    }
                    count -= 1;
                    if (count === 0){
                        self.results(nodes);
                        self.currentPage(self.pageToGet());
                        self.numberOfPages(Math.ceil(response.links.meta.total / response.links.meta.per_page));
                        self.addNewPaginators();
                    }
                });
                self.doneSearching();
            });
            requestNodeLinks.fail(function(xhr){
                self.searchWarningMsg(xhr.responseJSON && xhr.responseJSON.message_long);
                count -= 1;
                if (count === 0){
                    self.results(nodes);
                    self.currentPage(self.pageToGet());
                    self.numberOfPages(Math.ceil(response.links.meta.total / response.links.meta.per_page));
                    self.addNewPaginators();
                }
                self.doneSearching();
            });
        });
        requestNodes.fail(function(xhr){
            self.searchWarningMsg(xhr.responseJSON && xhr.responseJSON.message_long);
            self.doneSearching();
        });
    },
    add: function(data){
        var self = this;
        var type = self.inputType() === 'nodes' ? 'node_links' : 'registration_links';
        var addUrl = osfHelpers.apiV2Url('nodes/' + nodeId + '/' + type + '/', {});
        var request = osfHelpers.ajaxJSON(
            'POST',
            addUrl,
            {
                'isCors': true,
                'data': {
                    'data': {
                        'type': type,
                        'relationships': {
                            'nodes': {
                                'data': {
                                    'type': self.inputType(),
                                    'id': data.id
                                }
                            }
                        }
                    }
                }
            }
        );
        request.done(function (response){
            self.dirty(true);
            self.selection.push(data);
        });
        request.fail(function(xhr){
            self.searchWarningMsg(xhr.responseJSON && xhr.responseJSON.message_long);
        });
    },
    remove: function(data){
        var self = this;
        var requestNodeLinks = osfHelpers.ajaxJSON(
            'GET',
            nodeLinksUrl,
            {'isCors': true}
        );
        requestNodeLinks.done(function(response){
            var nodeLinkId;
            for (var i = 0; i < response.data.length; i++){
                if (response.data[i].embeds.target_node.data.id === data.id){
                    nodeLinkId = response.data[i].id;
                    break;
                }
            }
            var type = self.inputType() === 'nodes' ? '/node_links/' : '/registration_links/';
            var deleteUrl = osfHelpers.apiV2Url('nodes/' + nodeId + type + nodeLinkId + '/', {});
            osfHelpers.ajaxJSON(
                'DELETE',
                deleteUrl,
                {'isCors': true}
            ).done(function(response){
                self.selection.splice(
                    self.selection.indexOf(data), 1
                );
                self.dirty(true);
            }).fail(function(xhr){
                self.searchWarningMsg(xhr.responseJSON && xhr.responseJSON.message_long);
            });
        });
        requestNodeLinks.fail(function(xhr){
            self.searchWarningMsg(xhr.responseJSON && xhr.responseJSON.message_long);
        });
    },
    selected: function(data){
        var self = this;
        for (var idx = 0; idx < self.selection().length; idx++){
            if (data.id === self.selection()[idx].id){
                return true;
            }
        }
        return false;
    },
    authorText: function(node){
        var contributors = node.embeds.contributors.data;
        var author = contributors[0].embeds.users.data.attributes.family_name;
        if (contributors.length > 1){
            author += ' et al.';
        }
        return author;
    },
    nodeView: function(){
        var self = this;
        if (self.inputType() !== 'nodes'){
            $('#getLinksRegistrationsTab').removeClass('active');
            $('#getLinksNodesTab').addClass('active');
            self.inputType('nodes');
            self.searchMyProjects();
        }
    },
    registrationView: function(){
        var self = this;
        if (self.inputType() !== 'registrations'){
            $('#getLinksNodesTab').removeClass('active');
            $('#getLinksRegistrationsTab').addClass('active');
            self.inputType('registrations');
            self.searchMyProjects();
        }
    },
    getDates: function(data){
        var date = '';
        if (data.type === 'registrations'){
            date = 'Registered: ' + data.dateRegistered.local;
        } else {
            date = 'Created: ' + data.dateCreated.local + '\nModified: ' + data.dateModified.local;
        }
        return date;
    },
    clear: function (){
        var self = this;
        if (self.query()){
            self.query('');
            self.results([]);
        }
        self.errorMsg('');
        self.searchWarningMsg('');
    },
    done: function(){
        var self = this;
        if (! self.dirty()) {
          self.clear();
          return false;
        }
        window.location.reload();
    }
});

var LinksViewModel = function($elm){
    var self = this;
    self.links = ko.observableArray([]);
    $elm.on('shown.bs.modal', function(){
        if (self.links().length === 0){
            $.ajax({
                type: 'GET',
                url: nodeApiUrl + 'pointer/',
                dataType: 'json'
            }).done(function(response){
                self.links(response.pointed);
            }).fail(function(){
                $elm.modal('hide');
                osfHelpers.growl('Error:', 'Could not get links');
            });
        }
    });

};

////////////////
// Public API //
////////////////

function PointerManager(selector, nodeName){
    var self = this;
    self.selector = selector;
    self.$element = $(self.selector);
    self.nodeName = nodeName;
    self.viewModel = new AddPointerViewModel(nodeName);
    self.init();
}

PointerManager.prototype.init = function(){
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
    self.$element.on('hidden.bs.modal', function(){
        self.viewModel.clear();
    });
};

function PointerDisplay(selector){
    this.selector = selector;
    this.$element = $(selector);
    this.viewModel = new LinksViewModel(this.$element);
    ko.applyBindings(this.viewModel, this.$element[0]);
}

module.exports = {
    PointerManager: PointerManager,
    PointerDisplay: PointerDisplay
};

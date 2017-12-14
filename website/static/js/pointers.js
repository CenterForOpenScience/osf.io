/**
 * Controls the "Add Links" modal.
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('js/osfHelpers');

var Paginator = require('js/paginator');
var oop = require('js/oop');
var Raven = require('raven-js');

// Grab nodeID from global context (mako)
var nodeApiUrl = window.contextVars.node.urls.api;
var nodeId = window.contextVars.node.id;
var nodeLinksUrl = $osf.apiV2Url(
  'nodes/' + nodeId + '/node_links/', {
    query : {
      'fields[nodes]' : 'relationships'
    }
  }
);

var SEARCH_ALL_SUBMIT_TEXT = 'Search all projects';
var SEARCH_MY_PROJECTS_SUBMIT_TEXT = 'Search my projects';
var SEARCHING_TEXT = 'Searching...';

var AddPointerViewModel = oop.extend(Paginator, {
    constructor: function(nodeTitle){
        var self = this;
        this.super.constructor.call(this);
        this.nodeTitle = nodeTitle;
        this.submitEnabled = ko.observable(true);
        this.query = ko.observable();
        this.results = ko.observableArray();
        this.selection = ko.observableArray();
        this.errorMsg = ko.observable('');
        this.totalPages = ko.observable(0);
        this.includePublic = ko.observable(false);
        this.processing = ko.observable(false);
        this.disableButtons = ko.pureComputed(function(){
            return self.processing() ? 'disabled' : '';
        });
        this.isClicked = ko.observable('');
        this.dirty = false;
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
        this.searchAllProjectsSubmitText = ko.pureComputed(function(){
            if (self.loadingResults() && self.includePublic()){
                return SEARCHING_TEXT;
            }
            return SEARCH_ALL_SUBMIT_TEXT;
        });
        this.searchMyProjectsSubmitText = ko.pureComputed(function(){
            if (self.loadingResults() && ! self.includePublic()){
                return SEARCHING_TEXT;
            }
            return SEARCH_MY_PROJECTS_SUBMIT_TEXT;
        });
    },
    doneSearching: function(){
        var self = this;
        self.loadingResults(false);
    },
    searchAllProjects: function(){
        var self = this;
        self.includePublic(true);
        self.pageToGet(0);
        self.fetchResults();
    },
    searchMyProjects: function(){
        var self = this;
        self.includePublic(false);
        self.pageToGet(0);
        self.fetchResults();
    },
    logErrors: function(url, status, error, msg){
        var self = this;
        Raven.captureMessage(msg, {
            extra: {
                url: url,
                status: status,
                error: error
            }
        });
        self.searchWarningMsg(msg);
    },
    cleanErrors: function(){
        var self = this;
        self.errorMsg('');
        self.searchWarningMsg('');
    },
    fetchResults: function(){
        var self = this;
        self.loadingResults(true);
        self.cleanErrors();
        self.results([]); // clears page for spinner
        self.selection([]);
        var pageNum = self.pageToGet() + 1;
        var userOrPublicNodes = self.includePublic() ? '' : 'users/me/';
        var url = $osf.apiV2Url(
             userOrPublicNodes + self.inputType() + '/', {
                query : {
                  'filter[title,id]' : self.query(),
                  'page' : pageNum,
                  'embed' : 'contributors',
                  'page[size]' : '4',
                  'filter[root][ne]' : nodeId
                }
            }
        );
        var requestNodes = $osf.ajaxJSON(
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
            var requestNodeLinks = $osf.ajaxJSON(
                'GET',
                nodeLinksUrl,
                {'isCors': true}
            );
            requestNodeLinks.done(function(responseNodelinks){
                var embedNodeIds = [];
                for (var i = 0; i < responseNodelinks.data.length; i++){
                    var target_node = responseNodelinks.data[i].embeds.target_node;
                    var embedId = target_node.data ? target_node.data.id :
                    responseNodelinks.data[i].relationships.target_node.links.related.href.split('/')[5];
                    embedNodeIds.push(embedId);
                }
                nodes.forEach(function(each){
                    if (each.type === 'registrations'){
                        each.dateRegistered = new $osf.FormattableDate(each.attributes.date_registered);
                    } else {
                        each.dateCreated = new $osf.FormattableDate(each.attributes.date_created);
                        each.dateModified = new $osf.FormattableDate(each.attributes.date_modified);
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
            requestNodeLinks.fail(function(xhr, status, error){
                count -= 1;
                if (count === 0){
                    self.results(nodes);
                    self.currentPage(self.pageToGet());
                    self.numberOfPages(Math.ceil(response.links.meta.total / response.links.meta.per_page));
                    self.addNewPaginators();
                }
                self.logErrors(nodeLinksUrl, status, error, 'Unable to retrieve project nodelinks');
                self.doneSearching();
            });
        });
        requestNodes.fail(function(xhr, status, error){
            var msg = 'Error retrieving nodes';
            Raven.captureMessage(msg, {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
            var typeProjects = self.includePublic() ? 'all' : 'user';
            self.logErrors(url, status, error, 'Unable to retrieve ' + typeProjects + ' projects');
            self.doneSearching();
        });
    },
    add: function(data){
        var self = this;
        self.processing(true);
        self.isClicked(data.id);
        self.cleanErrors();
        var addUrl = $osf.apiV2Url('nodes/' + nodeId + '/node_links/');
        var request = $osf.ajaxJSON(
            'POST',
            addUrl,
            {
                'isCors': true,
                'data': {
                    'data': {
                        'type': 'node_links',
                        'relationships': {
                            'nodes': {
                                'data': {
                                    'type': 'nodes',
                                    'id': data.id
                                }
                            }
                        }
                    }
                }
            }
        );
        request.done(function (response){
            self.selection.push(data);
            self.processing(false);
            self.dirty = true;
        });
        request.fail(function(xhr, status, error){
            self.logErrors(addUrl, status, error, 'Unable to link project');
            self.processing(false);
        });
    },
    remove: function(data){
        var self = this;
        self.processing(true);
        self.isClicked(data.id);
        self.cleanErrors();
        var requestNodeLinks = $osf.ajaxJSON(
            'GET',
            nodeLinksUrl,
            {'isCors': true}
        );
        requestNodeLinks.done(function(response){
            var nodeLinkId;
            for (var i = 0; i < response.data.length; i++){
                var target_node = response.data[i].embeds.target_node;
                var embedId = target_node.data ? target_node.data.id :
                    response.data[i].relationships.target_node.links.related.href.split('/')[5];
                if (embedId === data.id){
                    nodeLinkId = response.data[i].id;
                    break;
                }
            }
            var deleteUrl = $osf.apiV2Url('nodes/' + nodeId + '/node_links/' + nodeLinkId + '/');
            $osf.ajaxJSON(
                'DELETE',
                deleteUrl,
                {'isCors': true}
            ).done(function(response){
                self.selection.splice(
                    self.selection.indexOf(data), 1
                );
                self.processing(false);
                self.dirty = true;
            }).fail(function(xhr, status, error){
                self.logErrors(deleteUrl, status, error, 'Unable to remove nodelink');
                self.processing(false);
            });
        });
        requestNodeLinks.fail(function(xhr, status, error){
            self.logErrors(nodeLinksUrl, status, error, 'Unable to retrieve project nodelinks');
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
    title: function(node){
        var title = {'long': '', 'short': ''};
        title.long = node.attributes.title;
        title.short = node.attributes.title;
        if (node.attributes.title.length > 30){
            title.short = node.attributes.title.substr(0, 30) + '...';
        }
        return title;
    },
    authorText: function(node){
        var contributors = node.embeds.contributors.data;
        var author = $osf.findContribName(contributors[0].embeds.users.data.attributes);
        if (contributors.length > 1){
            author += ' et al.';
        }
        return author;
    },
    view: function(){
        var self = this;
        if (self.includePublic()){
            self.searchAllProjects();
        } else {
            self.searchMyProjects();
        }
    },
    nodeView: function(){
        var self = this;
        if (self.inputType() !== 'nodes'){
            $('#getLinksRegistrationsTab').removeClass('active');
            $('#getLinksNodesTab').addClass('active');
            self.inputType('nodes');
            self.view();
        }
    },
    registrationView: function(){
        var self = this;
        if (self.inputType() !== 'registrations'){
            $('#getLinksNodesTab').removeClass('active');
            $('#getLinksRegistrationsTab').addClass('active');
            self.inputType('registrations');
            self.view();
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
        self.results([]);
        self.cleanErrors();
        self.query('');
        if (self.dirty){
            window.location.reload();
        }
    },
    done: function(){
        var self = this;
        self.clear();
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
                $osf.growl('Error:', 'Could not get links');
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
    $('#linkProjects').on('click', function(){
        self.viewModel.searchMyProjects();
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

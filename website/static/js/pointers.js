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
        this.searchWarningMsg = ko.observable('');
        this.submitWarningMsg = ko.observable('');
        this.loadingResults = ko.observable(false);

        this.inputType = ko.observable('nodes');

        this.foundResults = ko.pureComputed(function() {
            return self.results().length;
        });

        this.noResults = ko.pureComputed(function() {
            return self.query() && !self.results().length;
        });
        this.searchMyProjects();
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
        self.results([]); // clears page for spinner
        self.selection([]);
        self.loadingResults(true); // enables spinner
        var query = '', myProjects = '', pageNum = self.pageToGet()+1;
        if (self.query()){
            query += 'filter[title]='+self.query()+'&';
        }
        if (!self.includePublic()){
            myProjects = 'users/me/';
        }
        var url = osfHelpers.apiV2Url(myProjects+self.inputType()+'/', {query: query+'page='+pageNum+'&embed=contributors&page[size]=5'});
        var request = osfHelpers.ajaxJSON(
            'GET',
            url,
            {'isCors': true});
        request.done(function(response) {
            var nodes = response.data;
            if (!nodes.length) {
                self.errorMsg('No results found.');
            }
            else {
                var count = nodes.length;
                nodes.forEach(function(each) {
                    if (each.type === 'registrations') {
                        each.dateRegistered = new osfHelpers.FormattableDate(each.attributes.date_registered);
                    } else {
                        each.dateCreated = new osfHelpers.FormattableDate(each.attributes.date_created);
                        each.dateModified = new osfHelpers.FormattableDate(each.attributes.date_modified);
                    }
                    each.link = '';
                    var url = osfHelpers.apiV2Url('nodes/'+nodeId+'/node_links/', {});
                    var request = osfHelpers.ajaxJSON(
                        'GET',
                        url,
                        {'isCors': true});
                    request.done(function(nl_response) {
                        var result = nl_response.data;
                        var i;
                        for (i = 0; i < result.length; i++) {
                            if (result[i].embeds.target_node.data.id === each.id) {
                                self.selection.push(each);
                                break;
                            }
                        }
                        if (--count === 0) {
                            self.results(nodes);
                            self.currentPage(self.pageToGet());
                            self.numberOfPages(Math.ceil(response.links.meta.total / response.links.meta.per_page));
                            self.addNewPaginators();
                        }
                    });
                    request.fail(function(xhr) {
                        self.searchWarningMsg(xhr.responseJSON && xhr.responseJSON.message_long);
                        if (--count === 0) {
                            self.results(nodes);
                            self.currentPage(self.pageToGet());
                            self.numberOfPages(Math.ceil(response.links.meta.total / response.links.meta.per_page));
                            self.addNewPaginators();
                        }
                    });
                });
            }
        });
        request.fail(function(xhr) {
            self.searchWarningMsg(xhr.responseJSON && xhr.responseJSON.message_long);
        });
        self.searchAllProjectsSubmitText(SEARCH_ALL_SUBMIT_TEXT);
        self.searchMyProjectsSubmitText(SEARCH_MY_PROJECTS_SUBMIT_TEXT);
        self.loadingResults(false);
    },
    addTips: function(elements, data) {
        elements.forEach(function(element) {
            var titleText = '';
            if (data.type === 'registrations') {
                titleText = 'Registered: ' + data.dateRegistered.local;
            } else {
                titleText = 'Created: ' + data.dateCreated.local + '\nModified: ' + data.dateModified.local;
            }
            $(element).tooltip({
                title: titleText
            });
        });
    },
    add: function(data) {
        var self = this;
        if (self.inputType() === 'nodes') {
            var url = osfHelpers.apiV2Url('nodes/'+nodeId+'/node_links/', {});
            var request = osfHelpers.ajaxJSON(
                'POST',
                url,
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
                });
            request.done(function (response) {
                    self.selection.push(data);
            });
        }
        else{
            // BLOCKER
            // var url = osfHelpers.apiV2Url('nodes/'+nodeId+'/registration_links/', {});
            // var request = osfHelpers.ajaxJSON(
            //     'POST',
            //     url,
            //     {
            //         'isCors': true,
            //         'data': {
            //             'data': {
            //                 'type': 'registration_links',
            //                 'relationships': {
            //                     'nodes': {
            //                         'data': {
            //                             'type': 'registrations',
            //                             'id': data.id
            //                         }
            //                     }
            //                 }
            //             }
            //         }
            //     });
            // request.done(function (response) {
            //     self.selection.push(data);
            // });
        }
    },
    remove: function(data) {
        var self = this;
        if (self.inputType() === 'nodes'){
            var url = osfHelpers.apiV2Url('nodes/'+nodeId+'/node_links/', {});
            var request = osfHelpers.ajaxJSON(
                'GET',
                url,
                {'isCors': true});
            request.done(function(response) {
                var i, nl_id;
                for (i = 0; i < response.data.length; i++){
                    if (response.data[i].embeds.target_node.data.id === data.id){
                        nl_id = response.data[i].id;
                    }
                }
                var url = osfHelpers.apiV2Url('nodes/'+nodeId+'/node_links/'+nl_id+'/', {});
                var request = osfHelpers.ajaxJSON(
                    'DELETE',
                    url,
                    {
                        'isCors': true
                    });
                request.done(function(nl_response) {
                    self.selection.splice(
                        self.selection.indexOf(data), 1
                    );
                });
            });
        }
        else {
            // BLOCKER
            // var url = osfHelpers.apiV2Url('nodes/'+nodeId+'/registration_links/', {});
            // var request = osfHelpers.ajaxJSON(
            //     'GET',
            //     url,
            //     {'isCors': true});
            // request.done(function(response) {
            //     var i, nl_id;
            //     for (i = 0; i < response.data.length; i++){
            //         if (response.data[i].embeds.target_node.data.id === data.id){
            //             nl_id = response.data[i].id;
            //         }
            //     }
            //     var url = osfHelpers.apiV2Url('nodes/'+nodeId+'/registration_links/'+nl_id+'/', {});
            //     var request = osfHelpers.ajaxJSON(
            //         'DELETE',
            //         url,
            //         {
            //             'isCors': true
            //         });
            //     request.done(function(nl_response) {
            //         self.selection.splice(
            //             self.selection.indexOf(data), 1
            //         );
            //     });
            // });
        }

    },
    // addAll: function() {
    //     var self = this;
    //     $.each(self.results(), function(idx, result) {
    //         if (self.selection().indexOf(result) === -1) {
    //             self.add(result);
    //         }
    //     });
    // },
    // removeAll: function() {
    //     var self = this;
    //     $.each(self.selection(), function(idx, selected) {
    //         self.remove(selected);
    //     });
    // },
    selected: function(data) {
        var self = this;
        for (var idx = 0; idx < self.selection().length; idx++) {
            if (data.id === self.selection()[idx].id) {
                return true;
            }
        }
        return false;
    },
    // submit: function() {
    //     var self = this;
    //     self.submitEnabled(false);
    //     self.submitWarningMsg('');
    //
    //     var nodeIds = osfHelpers.mapByProperty(self.selection(), 'id');
    //
    //     osfHelpers.postJSON(
    //         nodeApiUrl + 'pointer/', {
    //             nodeIds: nodeIds
    //         }
    //     ).done(function() {
    //         window.location.reload();
    //     }).fail(function(data) {
    //         self.submitEnabled(true);
    //         self.submitWarningMsg(data.responseJSON && data.responseJSON.message_long);
    //     });
    // },
    // clear: function() {
    //     this.query('');
    //     this.results([]);
    //     this.selection([]);
    //     this.searchWarningMsg('');
    //     this.submitWarningMsg('');
    // },
    authorText: function(node) {
        var contributors = node.embeds.contributors.data;
        var author = contributors[0].embeds.users.data.attributes.family_name;
        if (contributors.length > 1) {
            author += ' et al.';
        }
        return author;
    },
    nodeView: function() {
        var self = this;
        if (self.inputType() !== 'nodes') {
            $('#getLinksRegistrationsTab').removeClass('active');
            $('#getLinksNodesTab').addClass('active');
            self.inputType('nodes');
            self.searchMyProjects();
        }
    },
    registrationView: function() {
        var self = this;
        if (self.inputType() !== 'registrations') {
            $('#getLinksNodesTab').removeClass('active');
            $('#getLinksRegistrationsTab').addClass('active');
            self.inputType('registrations');
            self.searchMyProjects();
        }
    },
    done: function() {
        window.location.reload();
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

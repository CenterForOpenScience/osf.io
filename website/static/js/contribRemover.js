/**
 * Controller for the Add Contributor modal.
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');

var oop = require('./oop');
var $osf = require('./osfHelpers');
var Paginator = require('./paginator');

var NODE_OFFSET = 25;
// Max number of recent/common contributors to show
var MAX_RECENT = 5;


var RemoveContributorViewModel = oop.extend(Paginator, {
    constructor: function(title, parentId, parentTitle) {
        this.super.constructor.call(this);
        var self = this;
        self.title = title;
        self.parentId = parentId;
        self.parentTitle = parentTitle;

        self.page = ko.observable('whom');
        self.pageTitle = ko.computed(function() {
            return {
                whom: 'Remove Contributors',
                which: 'Select Components',
            }[self.page()];
        });


        self.query = ko.observable();
        self.results = ko.observableArray([]);
        self.contributors = ko.observableArray([]);
        self.selection = ko.observableArray([]);
        self.notification = ko.observable('');
        self.inviteError = ko.observable('');
        self.totalPages = ko.observable(0);
        self.nodes = ko.observableArray([]);
        self.nodesToChange = ko.observableArray();
        self.contributorsOnNodes = ko.observableArray([]);
        $.getJSON(
            nodeApiUrl + 'get_editable_children/', {},
            function(result) {
                $.each(result.children || [], function(idx, child) {
                    child.margin = NODE_OFFSET + child.indent * NODE_OFFSET + 'px';
                });
                result.node.margin = "0px"
                result.children.unshift(result.node)
                self.nodes(result.children);
            }
        );

       $.getJSON(
            nodeApiUrl + 'tordoff_get/', {},
            function(result) {
                self.contributorsOnNodes(result);
            }
        );


        $.getJSON(
            nodeApiUrl + 'get_contributors/', {},
                function(result) {
                    self.contributors(result.contributors);
                }
        );


        self.foundResults = ko.pureComputed(function() {
            return self.query() && self.results().length;
        });


        self.noResults = ko.pureComputed(function() {
            return self.query() && !self.results().length;
        });

        self.inviteName = ko.observable();
        self.inviteEmail = ko.observable();

        self.addingSummary = ko.computed(function() {
            var names = $.map(self.selection(), function(result) {
                return result.fullname;
            });
            return names.join(', ');
        });
    },
    selectWhom: function() {
        this.page('whom');
    },
    selectWhich: function() {
        this.page('which');
    },
    goToPage: function(page) {
        this.page(page);
    },
    contribNodes: function(node_id,contrib_id) {

           for(var i = 0;i < this.contributorsOnNodes()[node_id].length; i++){
              if(this.contributorsOnNodes()[node_id][i]["id"] == contrib_id){
              return true;
              }

          }



            return false;
    },
    startSearch: function() {
        this.currentPage(0);
        this.fetchResults();
    },
    fetchResults: function() {
        var self = this;

        self.notification(false);
        if (self.query()) {
            return $.getJSON(
                '/api/v1/user/search/', {
                    query: self.query(),
                    excludeNode: nodeId,
                    page: self.currentPage
                },
                function(contributors) {
                    self.results(contributors);
                    self.currentPage(result.page);
                    self.numberOfPages(result.pages);
                    self.addNewPaginators();
                }
            );
        } else {
            self.results([]);
            self.currentPage(0);
            self.totalPages(0);
        }
    },
    importFromParent: function() {
        var self = this;
        self.notification(false);
        $.getJSON(
            nodeApiUrl + 'get_contributors_from_parent/', {},
            function(result) {
                if (!result.contributors.length) {
                    self.notification({
                        'message': 'All contributors from parent already included.',
                        'level': 'info'
                    });
                }
                self.results(result.contributors);
            }
        );
    },
    addTips: function(elements) {
        elements.forEach(function(element) {
            $(element).find('.contrib-button').tooltip();
        });
    },
    afterRender: function(elm, data) {
        var self = this;
        self.addTips(elm, data);
    },
    makeAfterRender: function() {
        var self = this;
        return function(elm, data) {
            return self.afterRender(elm, data);
        };
    },
    add: function(data) {
        var self = this;
        // All manually added contributors are visible
        data.visible = true;
        this.selection.push(data);
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    },
    remove: function(data) {
        this.selection.splice(
            this.selection.indexOf(data), 1
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
    cantSelectNodes: function() {
        return this.nodesToChange().length === this.nodes().length;
    },
    cantDeselectNodes: function() {
        return this.nodesToChange().length === 0;
    },
    selectNodes: function() {
        var self = this;

        ko.utils.arrayMap(self.selection(), function(user) {
            self.selectNodesForContrib(user);
            }
            );

    },
    selectNodesForContrib: function(contrib) {
        var self = this;

        $.each(self.nodes(), function(idx,node) {
                $.each(self.contributorsOnNodes()[node.id], function(inx,contribOnNode) {
                    if(contrib.id == contribOnNode.id){
                        self.nodesToChange.push(contrib.id+"|"+node.id);
                    }
                });
            });


    },
    deselectNodesForContrib: function(contrib) {
         var self = this;

        self.nodesToChange.remove(function(item) { return item.split("|")[0] == contrib.id});
    },
    deselectNodes: function() {
        this.nodesToChange([]);
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
    listToRemove : function(){
        var self = this;

        self.ToRemove = {};
        ko.utils.arrayMap(self.nodes(), function(node) {
            self.ToRemove[node.id] = [];
            ko.utils.arrayMap(self.nodesToChange(), function(string) {
                if(string.split('|')[1] == node.id && self.ToRemove[node.id].indexOf(string.split('|')[0]) == -1){
                    self.ToRemove[node.id].push(string.split('|')[0]);
                }

                });
            });

            alert(ko.toJSON(self.ToRemove, null ,2));
            return self.ToRemove

    },


    submit: function(data) {
        var self = this;

        $osf.postJSON(
            nodeApiUrl + 'projectremovecontributors/',
                 {listToRemove :self.listToRemove()}
                    ).done(function() {
                            window.location.reload();

                    }).fail(function() {
                        $osf.growl("failed to remove contributors");
                        $osf.handleJSONError
                     });
    },
    clear: function() {
        var self = this;
        self.page('whom');
        self.query('');
        self.results([]);
        self.selection([]);
        self.nodesToChange([]);
        self.notification(false);
    }
});

////////////////
// Public API //
////////////////

function ContribRemover(selector, nodeTitle, nodeId, parentTitle) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.nodeTitle = nodeTitle;
    self.nodeId = nodeId;
    self.parentTitle = parentTitle;
    self.viewModel = new RemoveContributorViewModel(self.nodeTitle,
        self.nodeId, self.parentTitle);
    self.init();
}

ContribRemover.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
    // Clear popovers on dismiss start
    self.$element.on('hide.bs.modal', function() {
        self.$element.find('.popover').popover('hide');
    });
    // Clear user search modal when dismissed; catches dismiss by escape key
    // or cancel button.
    self.$element.on('hidden.bs.modal', function() {
        self.viewModel.clear();
    });
};

module.exports = ContribRemover;

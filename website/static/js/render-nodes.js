'use strict';

var $osf = require('js/osfHelpers');
var $ = require('jquery');
var ko = require('knockout');
var _ = require('js/rdmGettext')._;
var NodesDelete = require('js/nodesDelete');
var { Contributors } = require('js/contributors');

var ctx = window.contextVars;
var selector = '#containment';

window._ = _;

var NodeRenderViewModel = function (nodeData) {
    var self = this;

    self.domain = ctx.apiV1Domain;
    self.node = nodeData;
    this.contributors = new Contributors({
        contributors: self.node.contributors,
        others_count: self.node.others_count,
        nodeUrl: self.node.url,
    });

    self.localizedNodeType = ko.computed(function () {
        var nodeType = self.node.node_type;
        return _('Linked ' + localizeNodeType(nodeType));
    });

    self.displayText = ko.computed(function () {
        if (self.node.is_registration) {
            return 'Private Registration';
        } else if (self.node.is_fork) {
            return 'Private Fork';
        } else if (!self.node.primary) {
            return 'Private Link';
        } else {
            return 'Private Component';
        }
    });

    function localizeNodeType(nodeType) {
        var localizedNames = {
            project: _('Project'),
            component: _('Component'),
        };
        return localizedNames[nodeType] || nodeType;
    }
};

var NodesRenderViewModel = function () {
    var self = this;
    NodesDelete.NodesDeleteManager.call(self);
    self.apiUrl = ctx.node.urls.api;
    self.sortable = ko.observable(false);
    self.nodes = ko.observableArray([]);
    self.profile = ko.observableArray(null);
    self.user = ko.observable(Object.assign({}, {
            isProfile: false,
            permissions: {},
        }, ctx.currentUser || {})
    );

    self.hasPermission = function (permission) {
        var userValue = ko.unwrap(self.user);
        return (
            userValue && userValue.permissions && permission in userValue.permissions
        );
    };

    $.getJSON(self.apiUrl + 'components/', function (data) {
        data.nodes.map(function (nodeData) {
            self.nodes.push(new NodeRenderViewModel(nodeData));
        });
        self.sortable(data.user.can_sort);
        self.user(Object.assign(self.user, data.user));
    });
};

NodesRenderViewModel.prototype = Object.create(
    NodesDelete.NodesDeleteManager.prototype
);
NodesRenderViewModel.prototype.constructor = NodesRenderViewModel;

if ($(selector).length) {
    var viewModel = new NodesRenderViewModel();
    $osf.applyBindings(viewModel, selector);
}

'use strict';

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('./osfHelpers');

var NODE_OFFSET = 25;

// TODO: Remove dependency on global scope
var nodeApiUrl = window.contextVars.node.urls.api;

var PrivateLinkViewModel = function(url) {
    var self = this;

    self.url = url;
    self.title = ko.observable('');
    self.isPublic = ko.observable('');
    self.name = ko.observable(null);
    self.anonymous = ko.observable(false);
    self.pageTitle = 'Generate New Link to Share Project';
    self.errorMsg = ko.observable('');
    self.id = ko.observable('');

    self.nodes = ko.observableArray([]);
    self.nodesToChange = ko.observableArray();
    self.disableSubmit = ko.observable(false);
    self.submitText = ko.observable('Submit');

    self.isChildVisible = function(data) {
        return (self.nodesToChange().indexOf(data.parent_id) !== -1 ||  data.parent_id === self.id());
    };

    self.changingNodesCleaner = ko.computed(function(){
        self.nodesToChange();
        var unchecked = [];
        var index;
        for (index = 0; index < self.nodes().length; ++index) {
            var currentNode = self.nodes()[index];
            if(unchecked.indexOf(currentNode.parent_id) !== -1 && currentNode.parent_id !== self.id()){
                self.nodesToChange.remove(currentNode.id);
            }
            if(self.nodesToChange.indexOf(currentNode.id) === -1){
                unchecked.push(currentNode.id);
            }
        }
    });

    /**
    * Fetches the node info from the server and updates the viewmodel.
    */

    function onFetchSuccess(response) {
        self.title(response.node.title);
        self.isPublic(response.node.is_public);
        self.id(response.node.id);
        $.each(response.children, function(idx, child) {
            child.margin = NODE_OFFSET + child.indent * NODE_OFFSET + 'px';
        });
        self.nodes(response.children);
    }

    function onFetchError() {
        $osf.growl('Could not retrieve projects.', 'Please refresh the page or ' +
                'contact <a href="mailto: support@cos.io">support@cos.io</a> if the ' +
                'problem persists.');
    }

    function fetch() {
        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(
            onFetchSuccess
        ).fail(
            onFetchError
        );
    }

    // Initial fetch of data
    fetch();

    self.cantSelectNodes = function() {
        return self.nodesToChange().length === self.nodes().length;
    };
    self.cantDeselectNodes = function() {
        return self.nodesToChange().length === 0;
    };

    self.selectNodes = function() {
        self.nodesToChange($osf.mapByProperty(self.nodes(), 'id'));
    };

    self.deselectNodes = function() {
        self.nodesToChange([]);
    };

    self.submit = function() {

        self.disableSubmit(true);
        self.submitText('Please wait');

        $osf.postJSON(
            nodeApiUrl + 'private_link/',
            {
                node_ids: self.nodesToChange(),
                name: self.name(),
                anonymous: self.anonymous()
            }
        ).done(function() {
            window.location.reload();
        }).fail(function() {
            $osf.growl('Error:','Failed to create a view-only link.');
            self.disableSubmit(false);
            self.submitText('Submit');
        });
    };

    self.clear = function() {
        self.nodesToChange([]);
    };
};


function PrivateLinkManager (selector, url) {
    var self = this;
    self.viewModel = new PrivateLinkViewModel(url);
    $osf.applyBindings(self.viewModel, selector);
}
module.exports = PrivateLinkManager;

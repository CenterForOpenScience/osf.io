var $ = require('jquery');
var ko = require('knockout');
require('bootstrap-editable');
var bootbox = require('bootbox');
var ZeroClipboard = require('zeroclipboard');
var $osf = require('osf-helpers');

// Make sure ZeroClipboard finds the right flash file
ZeroClipboard.config({
    moviePath: '/static/vendor/bower_components/zeroclipboard/ZeroClipboard.swf'}
);

var LINK_CUTOFF = 2;

var updateClipboard = function(target) {

    var client = new ZeroClipboard( target );

    client.on('load', function(client) {

        client.on('complete', function(client, args) {
            this.blur();
        } );

        client.on('mousedown', function(client, args){
            $(this).addClass('active');
        });

        client.on('mouseup', function(client, args){
            $(this).removeClass('active');
        });

        client.on('mouseover', function(client, args){
            $(this).tooltip('show');
        });

        client.on('mouseout', function(client, args){
            $(this).tooltip('hide');
        });

    });

};

var setupEditable = function(elm, data) {
    var $elm = $(elm);
    var $editable = $elm.find('.link-name');
    $editable.editable({
        type: 'text',
        url: nodeApiUrl + 'private_link/edit/',
        placement: 'bottom',
        ajaxOptions: {
            type: 'PUT',
            dataType: 'json',
            contentType: 'application/json',
        },
        send: 'always',
        title: 'Edit Link Name',
        params: function(params){
            // Send JSON data
            params.pk = data.id;
            return JSON.stringify(params);
        },
        success: function(response, value) {
            data.name(value);
        },
        error: $osf.handleEditableError,
    });
};

function LinkViewModel(data, $root) {

    var self = this;

    self.$root = $root;
    $.extend(self, data);

    self.collapse = "Collapse";
    self.name = ko.observable(data.name);
    self.linkName = "Link Name";
    self.readonly = "readonly";
    self.selectText = "this.setSelectionRange(0, this.value.length);";

    self.collapseNode = ko.observable(false);
    self.dateCreated = new $osf.FormattableDate(data.date_created);
    self.linkUrl = ko.computed(function() {
        return self.$root.nodeUrl() + '?view_only=' + data.key;
    });
    self.nodesList = ko.observableArray(data.nodes.slice(0, LINK_CUTOFF));
    self.moreNode = ko.observable(data.nodes.length > LINK_CUTOFF);
    self.removeLink = "Remove this link";
    self.hasMoreText = ko.computed(function(){
        return 'Show ' + (data.nodes.length - LINK_CUTOFF).toString() + ' more...';
    });

    self.anonymousDisplay = ko.computed(function() {
        return data.anonymous ? 'Yes' : 'No';
    });

    self.displayAllNodes = function() {
        self.nodesList(data.nodes);
        self.moreNode(false);
        self.collapseNode(true);
    };
    self.displayDefaultNodes = function() {
        self.nodesList(data.nodes.slice(0, LINK_CUTOFF));
        self.moreNode(true);
        self.collapseNode(false);
    };

}

function ViewModel(url) {
    var self = this;
    self.url = url;
    self.privateLinks = ko.observableArray();
    self.nodeUrl = ko.observable(null);

    function onFetchSuccess(response) {
        var node = response.node;
        self.privateLinks(ko.utils.arrayMap(node.private_links, function(link) {
            return new LinkViewModel(link, self);
        }));
        self.nodeUrl(node.absolute_url);
    }

    function onFetchError() {
            $osf.growl('Could not retrieve view-only links.', 'Please refresh the page or ' +
                    'contact <a href="mailto: support@cos.io">support@cos.io</a> if the ' +
                    'problem persists.');
        }

    function fetch() {
        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json',
        }).done(
            onFetchSuccess
        ).fail(
            onFetchError
        );
    }

    fetch();

    self.removeLink = function(data) {
        var dataToSend = {
            'private_link_id': data.id
        };
        bootbox.confirm({
            title: 'Remove view only link?',
            message: 'Are you sure to remove this view only link?',
            callback: function(result) {
                if(result) {
                    $.ajax({
                    type: 'delete',
                    url: nodeApiUrl + 'private_link/',
                    contentType: 'application/json',
                    dataType: 'json',
                    data: JSON.stringify(dataToSend)
                }).done(function() {
                    self.privateLinks.remove(data);
                }).fail(function() {
                    $osf.growl('Error:','Failed to delete the private link.');
                });
                }
            }
        });
    };

    self.afterRenderLink = function(elm, data) {

        var $tr = $(elm);
        // Add this to client
        var target = $tr.find('.copy-button');
        updateClipboard(target);
        $tr.find('.remove-private-link').tooltip();
        setupEditable(elm, data);
    };

}

function PrivateLinkTable (selector, url) {
    var self = this;
    self.viewModel = new ViewModel(url);
    $osf.applyBindings(self.viewModel, selector);

}
module.exports = PrivateLinkTable;

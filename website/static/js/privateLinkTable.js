'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var $osf = require('./osfHelpers');
var clipboard = require('./clipboard');
require('js/osfToggleHeight');

require('bootstrap-editable');

var ctx = window.contextVars;

function LinkViewModel(data, $root) {

    var self = this;

    self.$root = $root;
    $.extend(self, data);

    self.name = ko.observable(data.name);
    self.readonly = 'readonly';
    self.selectText = 'this.setSelectionRange(0, this.value.length);';

    self.dateCreated = new $osf.FormattableDate(data.date_created);
    self.linkUrl = ko.computed(function() {
        return self.$root.nodeUrl() + '?view_only=' + data.key;
    });
    self.nodesList = ko.observableArray(data.nodes);

    self.anonymousDisplay = ko.computed(function() {
        var openTag = '<span>';
        var closeTag = '</span>';
        var text;
        if (data.anonymous) {
            text = 'Yes';
            // Strikethrough if node is public
            if ($root.nodeIsPublic) {
                openTag = '<del>';
                closeTag = '</del>';
            }
        } else{
            text = 'No';
        }
        return [openTag, text, closeTag].join('');
    });

    self.toggle = function(data, event) {
        event.target.select();
    };

    self.toggleExpand = function() {
        self.expanded(!self.expanded());
    };

    self.expanded = ko.observable(false);
}

function ViewModel(url, nodeIsPublic, table) {
    var self = this;
    self.nodeIsPublic = nodeIsPublic || false;
    self.url = url;
    self.privateLinks = ko.observableArray();
    self.nodeUrl = ko.observable(null);

    self.visible = ko.computed(function() {
        return self.privateLinks().length > 0;
    });

    function onFetchSuccess(response) {
        var node = response.node;
        self.privateLinks(ko.utils.arrayMap(node.private_links, function(link) {
            return new LinkViewModel(link, self);
        }));
        self.nodeUrl(node.absolute_url);
    }

    function onFetchError() {
        $osf.growl('Could not retrieve view-only links.', 'Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
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

    fetch();

    self.removeLink = function(data) {
        var dataToSend = {
            'private_link_id': data.id
        };
        bootbox.confirm({
            title: 'Remove view-only link?',
            message: 'Are you sure you want to remove this view-only link?',
            callback: function(result) {
                if(result) {
                    $.ajax({
                    type: 'delete',
                    url: ctx.node.urls.api + 'private_link/',
                    contentType: 'application/json',
                    dataType: 'json',
                    data: JSON.stringify(dataToSend)
                }).done(function() {
                    self.privateLinks.remove(data);
                }).fail(function() {
                    $osf.growl('Error:','Failed to delete the private link.');
                });
                }
            },
            buttons:{
                confirm:{
                    label:'Remove',
                    className:'btn-danger'
                }
            }
        });
    };

    self.setupEditable = function(elm, data) {
        var $elm = $(elm);
        var $editable = $elm.find('.link-name');
        $editable.editable({
            type: 'text',
            url: ctx.node.urls.api + 'private_link/edit/',
            placement: 'bottom',
            ajaxOptions: {
                type: 'PUT',
                dataType: 'json',
                contentType: 'application/json'
            },
            send: 'always',
            title: 'Edit Link Name',
            params: function(params){
                // Send JSON data
                params.pk = data.id;
                return JSON.stringify(params);
            },
            success: function(response) {
                data.name(response);
                fetch();
            },
            error: $osf.handleEditableError
        });
    };

    self.collapsed = ko.observable();

    self.afterRenderLink = function(elm, data) {
        var $tr = $(elm);
        if (self.privateLinks().indexOf(ko.dataFor($tr[1])) === 0) {
            self.onWindowResize();
        }
        var target = $tr.find('button>i.fa.fa-copy')[0].parentElement;
        clipboard(target);
        $tr.find('.remove-private-link').tooltip();
        self.setupEditable(elm, data);
        $('.private-link-list').osfToggleHeight({height: 50});
    };

    self.table = $(table);

    self.onWindowResize = function () {
        self.collapsed(self.table.children().filter('thead').is(':hidden'));
    };

}

function PrivateLinkTable (selector, url, nodeIsPublic, table) {
    var self = this;
    self.viewModel = new ViewModel(url, nodeIsPublic, table);
    $osf.applyBindings(self.viewModel, selector);

}
module.exports = PrivateLinkTable;

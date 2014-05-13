/**
 * app.js
 * Knockout models, ViewModels, and custom binders.
 */
// TODO: Currently, these all pollute global namespace. Move these to their
// own module.

////////////////
// ViewModels //
////////////////


var LinksViewModel = function(elm) {

    var self = this;
    self.links = ko.observableArray([]);

    $(elm).on('shown.bs.modal', function() {
        if (self.links().length == 0) {
            $.ajax({
                type: 'GET',
                url: nodeApiUrl + 'pointer/',
                dataType: 'json',
                success: function(response) {
                    self.links(response.pointed);
                },
                error: function() {
                    elm.modal('hide');
                    bootbox.alert('Could not get links');
                }
            });
        }
    });

};

var NODE_OFFSET = 25;
var PrivateLinkViewModel = function(title, parentId, parentTitle) {

    var self = this;

    self.title = title;
    self.parentId = parentId;
    self.parentTitle = parentTitle;
    self.label = ko.observable(null);
    self.pageTitle = 'Generate New Private Link';
    self.errorMsg = ko.observable('');

    self.nodes = ko.observableArray([]);
    self.nodesToChange = ko.observableArray();
    $.getJSON(
        nodeApiUrl + 'get_editable_children/',
        {},
        function(result) {
            $.each(result['children'], function(idx, child) {
                child['margin'] = NODE_OFFSET + child['indent'] * NODE_OFFSET + 'px';
            });
            self.nodes(result['children']);
        }
    );

    self.cantSelectNodes = function() {
        return self.nodesToChange().length == self.nodes().length;
    };
    self.cantDeselectNodes = function() {
        return self.nodesToChange().length == 0;
    };

    self.selectNodes = function() {
        self.nodesToChange(attrMap(self.nodes(), 'id'));
    };
    self.deselectNodes = function() {
        self.nodesToChange([]);
    };

    self.submit = function() {
        $.ajax(
            nodeApiUrl + 'private_link/',
            {
                type: 'post',
                data: JSON.stringify({
                    node_ids: self.nodesToChange(),
                    label: self.label()
                }),
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                    if (response.status === 'success') {
                        window.location.reload();
                    }
                }
            }
        )
    };

    self.clear = function() {
        self.nodesToChange([]);
    };
};



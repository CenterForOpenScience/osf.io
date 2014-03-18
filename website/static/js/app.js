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



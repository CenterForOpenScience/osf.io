/**
 * Controls the "Add Links" modal.
 */
(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        // TODO: Use require to load dependencies (jquery, knockout, etc.)
        define(['knockout'], factory);
    } else {
        global.Pointers = factory(global.ko);
    }
}(this, function(ko) {
    'use strict';

    var AddPointerViewModel = function(nodeTitle) {

        var self = this;

        self.nodeTitle = nodeTitle;
        self.submitEnabled = ko.observable(true);

        self.query = ko.observable();
        self.results = ko.observableArray();
        self.selection = ko.observableArray();
        self.errorMsg = ko.observable('');

        self.search = function(includePublic) {
            self.results([]);
            self.errorMsg('');
            $.osf.postJSON(
                '/api/v1/search/node/',
                {
                    query: self.query(),
                    nodeId: nodeId,
                    includePublic: includePublic
                }
            ).done(function(result) {
                if (!result.nodes.length) {
                    self.errorMsg('No results found.');
                }
                self.results(result.nodes);
            }).fail(
                $.osf.handleJSONError
            );
        };

        self.addTips = function(elements) {
            elements.forEach(function(element) {
                $(element).find('.contrib-button').tooltip();
            });
        };

        self.add = function(data) {
            self.selection.push(data);
            // Hack: Hide and refresh tooltips
            $('.tooltip').hide();
            $('.contrib-button').tooltip();
        };

        self.remove = function(data) {
            self.selection.splice(
                self.selection.indexOf(data), 1
            );
            // Hack: Hide and refresh tooltips
            $('.tooltip').hide();
            $('.contrib-button').tooltip();
        };

        self.addAll = function() {
            $.each(self.results(), function(idx, result) {
                if (self.selection().indexOf(result) === -1) {
                    self.add(result);
                }
            });
        };

        self.removeAll = function() {
            $.each(self.selection(), function(idx, selected) {
                self.remove(selected);
            });
        };

        self.selected = function(data) {
            for (var idx=0; idx < self.selection().length; idx++) {
                if (data.id === self.selection()[idx].id) {
                    return true;
                }
            }
            return false;
        };

        self.submit = function() {
            self.submitEnabled(false);
            var nodeIds = $.osf.mapByProperty(self.selection(), 'id');
            $.osf.postJSON(
                nodeApiUrl + 'pointer/',
                {nodeIds: nodeIds}
            ).done(function() {
                window.location.reload();
            }).fail( function(data) {
                    self.submitEnabled(true);
                    $.osf.handleJSONError(data);
                }
            );
        };

        self.clear = function() {
            self.query('');
            self.results([]);
            self.selection([]);
        };

        self.authorText = function(node) {
            var rv = node.firstAuthor;
            if (node.etal) {
                rv += ' et al.';
            }
            return rv;
        };

    };


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
                    $.osf.growl('Error:','Could not get links');
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

    return {
        PointerManager: PointerManager,
        PointerDisplay: PointerDisplay
    };

}));

/**
 * Components involving the typeahead.js autocomplete library.
 *
 * Inspired by the onboarder component, but refactored into a generic view-model
 * that can be subclassed to create components to search through lists of
 * objects other than nodes.
**/
'use strict';
require('css/autocomplete.css');

var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
require('typeahead.js');

var MethodNotDefined = function(methodName) {
    this.name = 'MethodNotDefined';
    this.message = methodName;
};
MethodNotDefined.prototype = Error.prototype;

/**
 * ViewModel for a generic typeahead search component.
 *
 * Template: osf-search in components/autocomplete.js
 *
 * Params:
 *  data: the URL from which to fetch the items to be searched
 *  inputElement: the element upon which to call .typeahead(). Injected during
 *      component registration.
 */
var BaseSearchViewModel = function (params) {
    // Parse params
    this.dataUrl = params.data;
    this.inputElement = params.inputElement;

    // Observables
    this.items = ko.observableArray();
    this.itemSelected = ko.observable(null);
    this.hasItemSelected = ko.pureComputed(function() {
        return this.itemSelected() !== null;
    }.bind(this));
    this.submitText = ko.observable(params.submitText || 'Submit');
    this.placeholder = params.placeholder || '';

    // Get the data and initialize the component
    this.fetchData().done(
        this.processData.bind(this),
        this.initTypeahead.bind(this)
    );
};
$.extend(BaseSearchViewModel.prototype, {
    /************************************************
     * Abstract methods - subclasses must implement *
     ************************************************/

    /** Populate `items` from the `data` returned in `fetchData` */
    processData: function(data) {
        throw new MethodNotDefined('processData');
    },
    /**
     * Given a list of typeahead items, return a function that accepts a query
     *  and a callback, and calls the callback with a list of matched items.
     */
    substringMatcher: function(items) {
        throw new MethodNotDefined('substringMatcher');
    },
    /** Given a typeahead item, return HTML to be displayed in the dropdown. */
    suggestionTemplate: function() {
        throw new MethodNotDefined('suggestionTemplate');
    },
    /** Called when the form is submitted */
    onSubmit: function() {
        throw new MethodNotDefined('onSubmit');
    },
    /** Get the data at the provided URL, return a promise */
    fetchData: function () {
        var self = this;
        return $.get(self.dataUrl).fail(
            function(xhr, status, error) {
                Raven.captureMessage('Could not GET autocomplete data', {
                    extra: {
                        url: self.dataUrl,
                        textStatus: status,
                        error: error
                    }
                });
            });
    },
    /** Initialize the Typeahead widget for the component */
    initTypeahead: function () {
        this.inputElement.typeahead({
            hint: false,
            highlight: true,
            minLength: 0
        }, {
            // name: 'projectSearch' + nodeType + namespace,
            displayKey: function(data) {
                return data.value.node.title;
            },
            templates: {
                suggestion: this.suggestionTemplate
            },
            source: this.substringMatcher(this.items())
        });

        this.inputElement.bind('typeahead:selected', function(event, item) {
            // Call the parent viewModel's onSelected
            this.onSelected(item.value);
        }.bind(this));
    },
    /** Clear the selection */
    onClear: function () {
        this.inputElement.typeahead('val', '');
        this.itemSelected(null);
    },
    /** Set the item as selected */
    onSelected: function (item) {
        this.itemSelected(item);
    }
});


var DraftRegistrationsSearchViewModel = function (params) {
    BaseSearchViewModel.apply(this, arguments);
};
$.extend(DraftRegistrationsSearchViewModel.prototype, BaseSearchViewModel.prototype, {
    processData: function (data) {
        this.items(data.draftRegistrations);
    },
    onSubmit: function () {
        // Redirect the user to continue the draft registration
        window.location = this.itemSelected().url;
    },
    suggestionTemplate: function(item) {
        var dateUpdated = new $osf.FormattableDate(item.value.dateUpdated);
        var dateInitiated = new $osf.FormattableDate(item.value.dateInitiated);
        // jQuery implicity escapes HTML
        return $('<div>').append(
            $('<p>', {
                text: item.value.node.title
            }).append(
                [
                    $('<p>').append(
                        $('<small>', {
                            className: 'm-l-md text-muted',
                            text: 'Initiated by: ' + item.value.initiator.name
                        })
                    ),
                    $('<p>').append(
                        $('<small>', {
                            className: 'm-l-md text-muted',
                            text: 'Initiated: ' + dateInitiated.local
                        })
                    ),
                    $('<p>').append(
                        $('<small>', {
                            className: 'm-l-md text-muted',
                            text: 'Last updated: ' + dateUpdated.local
                        })
                    )                    
                ]
            )                
        ).html();
    },
    substringMatcher: function(strs) {
        return function findMatches(q, cb) {
            var matches = [];
            var substrRegex = new RegExp(q, 'i');
            var count = 0;

            $.each(strs, function(i, str) {
                if (substrRegex.test(str.node.title)) {
                    count += 1;
                    matches.push({ value: str });
                }
            });

            cb(matches);
        };
    }
});


ko.components.register('osf-draft-registrations-search', {
    viewModel: {
        createViewModel: function(params, componentInfo) {
            var opts = $.extend({}, {
                inputElement: $(componentInfo.element).find('input.osf-typeahead')
            }, params);
            return new DraftRegistrationsSearchViewModel(opts);
        }
    },
    template: {element: 'osf-search'}
});

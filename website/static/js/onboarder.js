/**
 * Components and binding handlers for the dashboard "onboarding" interface.
 * Includes a custom component for OSF project typeahead search, as well
 * the viewmodels for each of the individual onboarding widgets.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'knockout'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['typeahead'], function() {
            factory(jQuery, ko);
            $script.done('onboarder');
        });
    } else {
        factory(jQuery, ko);
    }
}(this, function ($, ko) {
    'use strict';

    function noop() {}
    var MAX_RESULTS = 14;

    var substringMatcher = function(strs) {
        return function findMatches(q, cb) {

            // an array that will be populated with substring matches
            var matches = [];

            // regex used to determine if a string contains the substring `q`

            var substrRegex = new RegExp(q, 'i');
            var count = 0;
            // iterate through the pool of strings and for any string that
            // contains the substring `q`, add it to the `matches` array
            $.each(strs, function(i, str) {
                if (substrRegex.test(str.name)) {
                    count += 1;
                    // the typeahead jQuery plugin expects suggestions to a
                    // JavaScript object, refer to typeahead docs for more info
                    matches.push({ value: str });

                    //alex's hack to limit number of results
                    if(count > MAX_RESULTS){
                        return false;
                    }
                    // above you can return name or a dict of name/node id,
                }
                // add an event to the input box -- listens for keystrokes and if there is a keystroke then it should clearrr
                //
            });

            cb(matches);
        };
    };

    function initTypeahead(element, myProjects, viewModel, params){
        var $inputElem = $(element);
        $inputElem.typeahead({
            hint: false,
            highlight: true,
            minLength: 0
        },
        {
            // name: 'projectSearch' + nodeType + namespace,
            displayKey: function(data) {
                return data.value.name;
            },
            source: substringMatcher(myProjects)
        });

        $inputElem.bind('typeahead:selected', function(obj, datum) {
            $inputElem.css('background-color', '#f5f5f5')
                .attr('disabled', true)
                .css('border', '2px solid LightGreen');
            // Call the parent viewModel's onSelected
            var onSelected = params.onSelected || viewModel.onSelected;
            onSelected(datum.value);
        });
    }

    /**
     * Binding handler for attaching an OSF typeahead search input.
     * Takes an optional parameter onSelected, which is called when a project
     * is selected.
     *
     * Example:
     *
     *  <div data-bind="projectSearch: {onSelected: onSelected}></div>
     */
    var DEFAULT_FETCH_URL = '/api/v1/dashboard/get_nodes/';
    ko.bindingHandlers.projectSearch = {
        init: function(element, valueAccessor, allBindings, viewModel) {
            var params = valueAccessor();
            var url = params.url || DEFAULT_FETCH_URL;
            var request = $.getJSON(url, function (projects) {
                var myProjects = projects.nodes.map(
                    function(item){return {
                        name: item.title,
                        id: item.id,
                        urls: {
                            web: item.url,
                            api: item.api_url,
                            register: item.url + 'register/',
                        }
                    };
                });
                initTypeahead(element, myProjects, viewModel, params);
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Could not fetch dashboard nodes.', {
                    url: url, textStatus: textStatus, error: error
                });
            });
        }
    };

    /**
     * ViewModel for the OSF project typeahead search widget.
     *
     * Template: osf-project-search element in components/dashboard_templates.mako
     *
     * Params:
     *  onSubmit: Function to call on submit. Receives the selected item.
     */
    function ProjectSearchViewModel(params) {
        var self = this;
        self.params = params;
        self.heading = params.heading;
        /* Observables */
        self.taSelected = ko.observable(null);
        /* Computeds */
        self.hasSelected = ko.computed(function() {
            return self.taSelected() !== null;
        });
        /* Functions */
        self.onSubmit = function() {
            var func = params.onSubmit || noop;
            func(self.taSelected());
        };
        self.onSelected = function(selected) {
            self.taSelected(selected);
        };
    }

    ko.components.register('osf-project-search', {
        viewModel: ProjectSearchViewModel,
        template: {element: 'osf-project-search'}
    });

    /**
     * ViewModel for the onboarding project registration component.
     *
     * Template: osf-ob-register element in components/dashboard_templates.mako
     */
    function OBRegisterViewModel(params) {
        var self = this;
        self.params = params;
        /* Observables */
        self.isOpen = ko.observable(false);
        /* Functions */
        self.open = function() {
            self.isOpen(true);
        };
        self.close = function() {
            self.isOpen(false);
        };
        self.toggle = function() {
            if (!self.isOpen()) {
                self.open();
            } else {
                self.close();
            }
        };
        /* On submit, redirect to the selected page's registration page */
        self.onRegisterSubmit = function(selected) {
            window.location = selected.urls.register;
        };
    }

    ko.components.register('osf-ob-register', {
        viewModel: OBRegisterViewModel,
        template: {element: 'osf-ob-register'}
    });
}));

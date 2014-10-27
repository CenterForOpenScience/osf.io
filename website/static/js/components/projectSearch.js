;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'knockout'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['typeahead'], function() {
            factory(jQuery, ko);
            $script.done('projectSearch');
        });
    } else {
        factory(jQuery, ko);
    }
}(this, function ($, ko) {
    'use strict';


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
                if(count > 14){
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

    function initTypeahead(element, myProjects, viewModel, onSelected){
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
            // set the taSelected observable of the viewModel
            viewModel.taSelected(datum.value);
            onSelected();
        });
    }

    function noop() {}

    ko.bindingHandlers.projectSearch = {
        init: function(element, valueAccessor, allBindings, viewModel) {
            var params = valueAccessor();
            var url = params.url || '/api/v1/dashboard/get_nodes/';
            var onSelected = params.onSelected || noop;
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

                initTypeahead(element, myProjects, viewModel, onSelected.bind(viewModel));
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Could not fetch dashboard nodes.', {
                    url: url, textStatus: textStatus, error: error
                });
            });
        }
    };

    function ProjectSearchViewModel(params) {
        var self = this;

        self.taSelected = ko.observable(null); // set by typeahead

        self.heading = params.heading;
        self.hasSelected = ko.observable(false);
        self.onSubmit = params.onSubmit || noop;
        self.enableButton = function() {
            self.hasSelected(true);
        };
    }

    ko.components.register('osf-project-search', {
        viewModel: ProjectSearchViewModel,
        template: {element: 'osf-project-search'}
    });

    var OPEN_ICON = '/static/img/plus.png';
    var CLOSE_ICON = '/static/img/minus.png';
    function OBRegisterViewModel(params) {
        var self = this;
        self.isOpen = ko.observable(false);
        self.toggleIconSrc = ko.observable(OPEN_ICON);
        self.open = function() {
            self.isOpen(true);
            self.toggleIconSrc(CLOSE_ICON);
        };
        self.close = function() {
            self.isOpen(false);
            self.toggleIconSrc(OPEN_ICON);
        };
        self.toggle = function() {
            if (!self.isOpen()) {
                self.open();
            } else {
                self.close();
            }
        };
    }

    ko.components.register('osf-ob-register', {
        viewModel: OBRegisterViewModel,
        template: {element: 'osf-ob-register'}
    });

}));

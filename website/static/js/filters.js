'use strict';

var $ = require('jquery');

(function($){
    $.fn.filters = function (options) {
        /*
            options:
                callback:   -this is the function that should be called whenever a search/filter is applied.
                            -takes in two parameters, filtered & empty.
                            -filtered is a boolean that returns true if the number of items displayed is less than
                            the number of items being searched
                            -empty is a boolean that returns true if there are 0 items displayed after the filters are
                            applied
                groups:     -a dictionary of filter button groups
                            -key: the ID for the group of filter buttons
                            -value: a dictionary of options with the following format:
                                - {
                                    filter: (selector to be used for filtering),
                                    type: (currently the options are 'text' or 'checkbox'),
                                    buttons: {
                                        (buttonID): (value to match) (if type is 'text' the value is the string that
                                        should be matched.  if type is 'text' the value is the boolean that should be
                                        matched),
                                        ....
                                    }
                                }
                inputs:     -a dictionary of the search fields
                            -key: the ID for the search field
                            -value: the selector that this field should search against
         */
        var settings = $.extend({
            items: ['.items'],
            manualRemove: false
        }, options);

        var itemsSelector = settings.items.join();

        var filterConstraints = {};
        var searchConstraints = {};


        /**
         * checks an element to see if it should be displayed based on the current searches
         *
         * @param el - the element being checked
         *
         * @returns {boolean}
         */
        var search = function(el) {
            for (var key in searchConstraints) {
                if (searchConstraints.hasOwnProperty(key)) {
                    var content = $(el.querySelector(key)).text().toLowerCase();
                    var exists = content.indexOf(searchConstraints[key]);
                    if (exists === -1) {
                        return false;
                    }
                }
            }
            return true;
        };

        /**
         * checks an element to see if it should be displayed based on the current filters
         *
         * @param el
         *
         * @returns {boolean}
         */
        var filter = function(el) {
            for (var key in filterConstraints) {
                if (filterConstraints.hasOwnProperty(key)) {
                    var selector = settings.groups[key].filter;
                    var type = settings.groups[key].type;
                    var match = filterConstraints[key];
                    if (type === 'text') {
                        var content = $(el.querySelector(selector)).text();
                        if (match.indexOf(content) === -1) {
                            return false;
                        }
                    }
                    else if (type === 'checkbox') {
                        if (match.indexOf(el.querySelector(selector).checked) === -1) {
                            return false;
                        }
                    }
                }
            }
            return true;
        };


        /**
         * called every time a search parameter changes or a filter is toggled
         *
         * hides items that should now be hidden and shows anything that was hidden and now isn't
         *
         * if there is a callback function, this function calls that with 'filtered' and 'empty' parameters
         */
        var toggle = function() {
            var activeItems = $(itemsSelector);
            activeItems.slice().each(function() {
                var self = this;
                if (!search(self) || !filter(self)) {
                    activeItems.splice(activeItems.index(self), 1);
                    if (!settings.manualRemove) {
                        $(self).hide();
                    }
                }
            });
            if (!settings.manualRemove){
                activeItems.show();
            }
            if (settings.callback !== undefined) {
                var empty = [];
                var filtered = [];
                for (var i = 0, selector; selector = settings.items[i]; i ++) {
                    var active = activeItems.filter(selector);
                    var items = $(selector);
                    if (active.length < items.length) {
                        filtered.push(selector);
                    }
                    if (active.length === 0) {
                        empty.push(selector);
                    }
                }
                settings.callback(filtered, empty, activeItems);
            }
        };


        /**
         * called when a filter button is pressed
         *
         * updates the filter constraints and calls the 'toggle' function
         */
        var applyFilters = function() {
            var self = this;
            if (!!settings.toggleClass) {
                $(self).toggleClass(settings.toggleClass);
            }
            var group = self.parentElement.parentElement.id;
            var match = settings.groups[group].buttons[self.id];
            try {
                var index = filterConstraints[group].indexOf(match);
                if (index === -1) {
                    filterConstraints[group].push(match);
                }
                else {
                    filterConstraints[group].splice(index, 1);
                    if (filterConstraints[group].length === 0) {
                        delete filterConstraints[group];
                    }
                }
            }
            catch(TypeError) {
                filterConstraints[group] = [match];
            }
            toggle();
        };

        /**
         * initializes the buttons to filter out certain groups on click
         */
        for (var group in settings.groups) {
            if (settings.groups.hasOwnProperty(group)) {
                for (var value in settings.groups[group].buttons) {
                    if (settings.groups[group].buttons.hasOwnProperty(value)) {
                        $('#' + value).on('click', applyFilters);
                    }
                }
            }
        }


        /**
         * called when a search box is changed
         *
         * updates the search constraints and then calls the 'toggle' function
         */
        function keyupFunction() {
            var self = this;
            var selector = settings.inputs[self.id];
            searchConstraints[selector] = $(self).val().toLowerCase();
            toggle();
        }

        /**
         * initializes the search boxes
         */
        for (var key in settings.inputs) {
            if (settings.inputs.hasOwnProperty(key)) {
                $('#' + key).keyup(keyupFunction);
            }
        }
    };
}($));

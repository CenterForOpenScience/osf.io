'use strict';
var $ = require('jquery');
var $osf = require('js/osfHelpers');
require('css/typeahead.css');
require('typeahead.js');

var MAX_RESULTS = 14;

(function($) {
    $.fn.projectsSelect = function (options) {

        // Default options
        var settings = $.extend({
            data : [],
            complete: null
        }, options);

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

        this.typeahead({
                hint: false,
                highlight: true,
                minLength: 0
            },
            {
                // name: 'projectSearch' + nodeType + namespace,
                displayKey: function(data) {
                    return data.value.attributes.title;
                },
                templates: {
                    suggestion: function(data) {
                        return '<p>' + data.value.attributes.title + '</p> ' +
                            '<p><small class="m-l-md text-muted">'+
                            'modified ' + data.value.formattedDate.local +   '</small></p>';
                    }
                },
                source: substringMatcher(settings.data)
            });

        this.bind('typeahead:selected', function(obj, datum) {
            // Call the parent viewModel's onSelected
            console.log('selected');
        });

        return this;
    };

})($);

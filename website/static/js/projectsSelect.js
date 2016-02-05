'use strict';
var $ = require('jquery');
var $osf = require('js/osfHelpers');
require('css/typeahead.css');
require('typeahead.js');

var MAX_RESULTS = 10;

(function($) {
    $.fn.projectsSelect = function (options) {
        var settings = $.extend({
            data : [],
            type : 'project',
            complete: null
        }, options);
        var substringMatcher = function(data) {
            return function findMatches(q, cb) {
                var matches = []; // an array that will be populated with substring matches
                var title; // Title string;
                var substrRegex = new RegExp(q, 'i');// regex used to determine if a string contains the substring `q`
                var count = 0;
                $.each(data, function(i, str) {  // for any title that contains the substring `q`, add it to the `matches` array
                    if (str.attributes){ // case for api v2 projects data structure
                        title = str.attributes.title;
                    } else if(str.node){ // Case for draft registrations api call data structure
                        title = str.node.title;
                    } else {
                        title = '';
                    }
                    if (substrRegex.test(title)) {
                        count += 1;
                        // the typeahead jQuery plugin expects suggestions to a
                        // JavaScript object, refer to typeahead docs for more info
                        matches.push({ value: str });
                        //alex's hack to limit number of results
                        if(count > MAX_RESULTS){
                            return false;
                        }
                    }
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
                display: function(data) {
                    if(settings.type === 'registration'){
                        return data.value.node.title;
                    }
                    return data.value.attributes.title;
                },
                templates: {
                    suggestion: function(data) {
                        if(settings.type === 'registration'){
                            return '<p>' + data.value.node.title + '</p> ' +
                            '<p><small class="m-l-md text-muted">'+
                            'modified ' + data.value.dateUpdated +   '</small></p>';
                        }
                        return '<p>' + data.value.attributes.title + '</p> ' +
                            '<p><small class="m-l-md text-muted">'+
                            'modified ' + data.value.formattedDate.local +   '</small></p>';
                    }
                },
                source: substringMatcher(settings.data)
            });

        this.bind('typeahead:selected', function(event, data) {
            console.log('selected', event, data);
            if ( $.isFunction( settings.complete ) ) {
                settings.complete( event, data.value );
            }
        });

        return this;
    };

})($);

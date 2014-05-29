;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['typeahead'], function() {
            global.ProjectSearch = factory(jQuery);
            $script.done('projectSearch');
        });
    } else {
        global.ProjectSearch = factory(jQuery);
    }
}(this, function ($) {
    'use strict';

    var substringMatcher = function(strs) {
      return function findMatches(q, cb) {

        // an array that will be populated with substring matches
        var matches = [];

        // regex used to determine if a string contains the substring `q`
        var substrRegex = new RegExp(q, 'i');

        // iterate through the pool of strings and for any string that
        // contains the substring `q`, add it to the `matches` array
        $.each(strs, function(i, str) {
          if (substrRegex.test(str.name)) {
            // the typeahead jQuery plugin expects suggestions to a
            // JavaScript object, refer to typeahead docs for more info
            matches.push({ value: str });
            // above you can return name or a dict of name/node id, 
          }
        });

        cb(matches);
      };
    };
    function ProjectSearch() {
        var self = this;
        this.myProjects = [];

        $.getJSON('/api/v1/dashboard/get_nodes/', function (projects) {
            projects.nodes.forEach(function(item){
                self.myProjects.push(
                {
                    name: item.title,
                    node_id: item.id
                });
            });

            $('#input_project').bind('typeahead:selected', function(obj, datum) {
                $('#add_link').removeAttr('disabled');
                var linkID = datum.value.node_id;
                $('#add_link').prop('linkID', linkID);
            });


            $('#project-search .typeahead').typeahead({
                hint: true,
                highlight: true,
                minLength: 1
            },
            {
                name: 'states',
                displayKey: function(data){
                    return data.value.name;
                },
                source: substringMatcher(self.myProjects)
            });

            $('#add_link').click(function() {
                var url = '/'+ $('#add_link').prop('linkID') + '/register'; 
                window.location.replace(url);
            });
    
        });
    }
    return ProjectSearch;
}));

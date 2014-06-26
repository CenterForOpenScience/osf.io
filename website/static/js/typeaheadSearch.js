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
      // add an event to the input box -- listens for keystrokes and if there is a keystroke then it should clearrr
      //           
    });

    cb(matches);
  };
};
 

function TypeaheadSearch(namespace) {
        var self = this;
        this.myProjects = [];

        function makeName(name, api_url, nodes){
            var parentUrl = nodes[api_url.split('/')[4]];
            if(api_url.indexOf('/node/') > -1){
                nodes.forEach(function(node){
                    if(node.url === parentUrl){
                        return parentUrl + ': ' + name;
                    }
                });
            }}
        }
        
        // gets data from api route
        $.getJSON('/api/v1/dashboard/get_nodes/', function (projects) {
            projects.nodes.forEach(function(item){
                self.myProjects.push(
                {
                    // name: makeName(item.title, item.api_url, projects.nodes),
                    name: item.title,
                    node_id: item.id,
                    route: item.api_url,

                });
            });
            //  once a typeahead option is selected, enable the button and assign the add_link variable for use later
            $('#inputProject' + namespace).bind('typeahead:selected', function(obj, datum) {
                $('#addLink' + namespace).removeAttr('disabled');
                var linkID = datum.value.node_id;
                var routeID = datum.value.route;
                $('#inputProject' + namespace).css('border-color', 'lightgreen');
                $('#addLink' + namespace).prop('linkID', linkID);
                $('#addLink' + namespace).prop('routeID', routeID);
            });
            
            // Listener that disables button when nothing selected
            $('#inputProject' + namespace).keypress(function(){
                $('#addLink' + namespace).attr('disabled', true);
                $('#inputProject' + namespace).css('border-color', '');
                $('#addLink' + namespace).removeProp('linkID');
                $('#addLink' + namespace).removeProp('routeID');
            });

            // type ahead logic
            $('#projectSearch' + namespace + ' .typeahead').typeahead({
                hint: true,
                highlight: true,
                minLength: 1
            },
            {
                name: 'projectSearch' + namespace,
                displayKey: function(data){
                    return data.value.name;
                },
                source: substringMatcher(self.myProjects)
            });
        });
};

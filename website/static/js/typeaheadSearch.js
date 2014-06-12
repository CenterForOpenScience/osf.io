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

        // gets data from api route
        $.getJSON('/api/v1/dashboard/get_nodes/', function (projects) {
            projects.nodes.forEach(function(item){
                self.myProjects.push(
                {
                    name: item.title,
                    node_id: item.id
                });
            });
            //  once a typeahead option is selected, enable the button and assign the add_link variable for use later
            $('#input_project_' + namespace).bind('typeahead:selected', function(obj, datum) {
                $('#add_link_' + namespace).removeAttr('disabled');
                var linkID = datum.value.node_id;
                $('#input_project_' + namespace).css("border-color", "lightgreen");
                $('#add_link_' + namespace).prop('linkID', linkID);
            });
            
            // Listener that disables button when nothing selected
            $('#input_project_' + namespace).keypress(function(){
                $('#add_link_' + namespace).attr('disabled', true);
                $('#input_project_' + namespace).css("border-color", "");
                $('#add_link_' + namespace).removeProp('linkID');
            });

            // type ahead logic
            $('#project-search_' + namespace + ' .typeahead').typeahead({
                hint: true,
                highlight: true,
                minLength: 1
            },
            {
                name: 'project_search' + namespace,
                displayKey: function(data){
                    return data.value.name;
                },
                source: substringMatcher(self.myProjects)
            });
        });
}

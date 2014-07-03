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
 
function TypeaheadSelectedOption(inputProject, clearInputProject, addLink, namespace, nodeType, componentBool){
//  once a typeahead option is selected, enable the button and assign the add_link variable for use later
    inputProject.bind('typeahead:selected', function(obj, datum) {
        var linkID = datum.value.node_id;
        var routeID = datum.value.route;
        clearInputProject.show();

        inputProject.css('background-color', '#f5f5f5')
            .attr('disabled', true)
            .css('border', '2px solid LightGreen');

        addLink.prop('linkID', linkID)
            .removeAttr('disabled')
            .prop('routeID', routeID);
        if(componentBool===1){
            console.log('this');

            parent_node = $('#addLink' + namespace).prop('linkID');
            $.getJSON('/api/v1/project/'+ parent_node +'/get_children/', function (projects) {
            var myProjects = projects.nodes.map(
                function(item){return {
                    'name': item.title,
                    'node_id': item.id,
                    'route': item.api_url,
                };
            });
              $('#inputComponent' + namespace).data('ttTypeahead').dropdown.datasets[0].source = substringMatcher(myProjects);

            $('#inputComponent' + namespace).attr('disabled', false);
            });
        }
    });
}


function TypeaheadAddListenter(clearInputProject, inputProject, addLink, namespace, nodeType, componentBool){
    clearInputProject[0].addEventListener('click', function() {

        clearInputProject.hide();
        
        inputProject.attr('disabled', false)
            .css('background-color', '')
            .css('border-color','#ccc')
            .val('');

        addLink.removeProp('linkID')
            .removeProp('routeID')
            .attr('disabled', true);
        if(componentBool===1){
            $('#inputComponent' + namespace).attr('disabled', true);      
        }
    });
}

function TypeaheadLogic(nodeType, namespace, myProjects){
    $('#input' + nodeType + namespace).typeahead({
        hint: true,
        highlight: true,
        minLength: 1
    },
    {
        name: 'projectSearch' + nodeType + namespace,
        displayKey: function(data){
            return data.value.name;
    },
        source: substringMatcher(myProjects)
    });
    // $('#input' + nodeType + namespace).data('typeahead');
}

function TypeaheadComponent(namespace, nodeType, componentBool){
        var myProjects = [];
        var $addLink = $('#addLink' + namespace);
        var $clearInputProject = $('#clearInput' + nodeType + namespace);
        var $inputProject = $('#input'+ nodeType + namespace); 

        TypeaheadSelectedOption($inputProject, $clearInputProject, $addLink, namespace, nodeType, componentBool);
        TypeaheadAddListenter($clearInputProject, $inputProject, $addLink, namespace, nodeType, componentBool);
        TypeaheadLogic(nodeType, namespace, myProjects);
}

function TypeaheadProject(namespace, nodeType, componentBool){
    $.getJSON('/api/v1/dashboard/get_nodes/', function (projects) {

        var myProjects = projects.nodes.map(
            function(item){return {
                'name': item.title,
                'node_id': item.id,
                'route': item.api_url,
            };
        });

        var $addLink = $('#addLink' + namespace);
        var $clearInputProject = $('#clearInput' + nodeType + namespace);
        var $inputProject = $('#input'+ nodeType + namespace); 
        
        TypeaheadSelectedOption($inputProject, $clearInputProject, $addLink, namespace, nodeType, componentBool);
        TypeaheadAddListenter($clearInputProject, $inputProject, $addLink, namespace, nodeType, componentBool);
        TypeaheadLogic(nodeType, namespace, myProjects);            
    });
}

function TypeaheadSearch(namespace, nodeType, componentBool) {
    if(nodeType==='Project'){
        TypeaheadProject(namespace, nodeType, componentBool);
    }else{
        TypeaheadComponent(namespace, nodeType, componentBool);
    }
}


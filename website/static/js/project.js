/////////////////////
// Project JS      //
/////////////////////
(function(){

// Messages, e.g. for confirmation dialogs, alerts, etc.
Messages = {
    makePublicWarning: 'Once a project is made public, there is no way to guarantee that ' +
                        'access to the data it contains can be complete prevented. Users ' +
                        'should assume that once a project is made public, it will always ' +
                        'be public. Are you absolutely sure you would like to continue?',

    makePrivateWarning: 'Making a project will prevent users from viewing it on this site, ' +
                        'but will have no impact on external sites, including Google\'s cache. ' +
                        'Would you like to continue?'
}

/* Utility Methods */

/**
 * Return the id of the current node by parsing the current URL.
 */
nodeToUse = function(){
  if(location.pathname.match("\/project\/.*\/node\/.*")){
    return location.pathname.match("\/project\/.*?\/node\/(.*?)\/.*")[1];
  }else{
    return location.pathname.match("\/project\/(.*?)\/.*")[1];
  }
}


/**
 * Return the api url for the current node by parsing the current URL.
 */
nodeToUseUrl = function(){
  if (location.pathname.match("\/project\/.*\/node\/.*")) {
    return '/api/v1' + location.pathname.match("(\/project\/.*?\/node\/.*?)\/.*")[1];
  } else {
    return '/api/v1' + location.pathname.match("(\/project\/.*?)\/.*")[1];
  }
}

// TODO: Move Watch and Fork click handlers to this file so that NodeActions
// doesn't need to be in global namespace
window.NodeActions = {};  // Namespace for NodeActions

NodeActions.forkNode = function(){
    $.ajax({
        url: nodeToUseUrl() + "/fork/",
        type: "POST",
    }).done(function(response) {
        window.location = response;
    });
};

/*
Toggles the watch mode ("watched" or "unwatched") when for a node at the
project view page.
*/
NodeActions.toggleWatch = function () {
    // Send POST request to node's watch API url and update the watch count
    $.ajax({
        url: nodeToUseUrl() + "/togglewatch/",
        type: "POST",
        dataType: "json",
        data: JSON.stringify({}),
        contentType: "application/json",
        success: function(data, status, xhr) {
            // Update watch count in DOM
            $watchCount = $("#watchCount");
            if (data["watched"]) { // If the user is watching
                $watchCount.html("Unwatch&nbsp;" + data["watchCount"]);
            } else {
                $watchCount.html("Watch&nbsp;" + data["watchCount"]);
            };
        }
    });
}

NodeActions.addNodeToProject = function(node, project){
    $.ajax({
       url:"/project/" + project + "/addnode/" + node,
       type:"POST",
       data:"node="+node+"&project="+project}).done(function(msg){
           $('#node'+node).removeClass('primary').addClass('success');
           $('#node'+node).onclick = function(){};
           $('#node'+node).html('Added');
       });
};

NodeActions.removeUser = function(userid, name) {
    bootbox.confirm('Remove ' + name + ' from contributor list?', function(result) {
        if (result) {
            $.ajax({
                type: "POST",
                url: nodeToUseUrl() + "/removecontributors/",
                contentType: "application/json",
                dataType: "json",
                data: JSON.stringify({
                    "id": userid,
                    "name": name,
                })
            }).done(function(response) {
                window.location.reload();
            });
        }
    });
    return false;
};

NodeActions._openCloseNode = function(node_id) {

    var icon = $("#icon-" + node_id),
        body = $("#body-" + node_id);

    body.toggleClass('hide');

    if ( body.hasClass('hide') ) {
        icon.removeClass('icon-minus');
        icon.addClass('icon-plus');
    }else{
        icon.removeClass('icon-plus');
        icon.addClass('icon-minus');
    }
}

/*
Display recent logs for for a node on the project view page.
*/
NodeActions.openCloseNode = function(node_id){
    var logs = $('#logs-' + node_id);
    if (logs.html() === "") {
        $.get(
            logs.attr('data-uri'),
            {count: 3},
            function(response) {
                logs.html(response);
                NodeActions._openCloseNode(node_id);
            }
        );
    } else {
        NodeActions._openCloseNode(node_id);
    }
};


/////////////////////
// Knockout Models //
/////////////////////

/**
 * The project model.
 */
// var Project = function(params) {
//     this._id =  params._id
//     this.api_url = params.api_url
// }

var ProjectViewModel = function() {
    var self = this;
    self.project = {};

    $.getJSON(nodeToUseUrl(), function(data){
        self.project = data;
    });


    self.toggleWatch = function() {
        // Send POST request to node's watch API url and update the watch count
        $.ajax({
            url: nodeToUseUrl() + "/togglewatch/",
            type: "POST",
            dataType: "json",
            data: JSON.stringify({}),
            contentType: "application/json",
            success: function(data, status, xhr) {
                // Update watch count in DOM
                $watchCount = $("#watchCount");
                if (data["watched"]) { // If the user is watching
                    $watchCount.html("Unwatch&nbsp;" + data["watchCount"]);
                } else {
                    $watchCount.html("Watch&nbsp;" + data["watchCount"]);
                };
            }
        });
    }
}

var addContributorModel = function(initial) {

    var self = this;

    self.query = ko.observable('');
    self.results = ko.observableArray(initial);
    self.selection = ko.observableArray([]);

    self.search = function() {
        $.getJSON(
            '/api/v1/user/search/',
            {query: self.query()},
            function(result) {
                self.results(result);
            }
        )
    };

    self.addTips = function(elements, data) {
        elements.forEach(function(element) {
            $(element).find('.contrib-button').tooltip();
        });
    };

    self.add = function(data, element) {
        self.selection.push(data);
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    };

    self.remove = function(data, element) {
        self.selection.splice(
            self.selection.indexOf(data), 1
        );
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    };

    self.selected = function(data) {
        for (var idx=0; idx < self.selection().length; idx++) {
            if (data.id == self.selection()[idx].id)
                return true;
        }
        return false;
    };

    self.submit = function() {
        var user_ids = self.selection().map(function(elm) {
            return elm.id;
        });
        $.ajax(
            nodeToUseUrl() + '/addcontributors/',
            {
                type: 'post',
                data: JSON.stringify({user_ids: user_ids}),
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                    if (response.status === 'success') {
                        window.location.reload();
                    }
                }
            }
        )
    };

    self.clear = function() {
        self.query('');
        self.results([]);
        self.selection([]);
    };

};


$(document).ready(function() {

    // Initiated addContributorsModel
    var $addContributors = $('#addContributors');
    viewModel = new addContributorModel();
    ko.applyBindings(viewModel, $addContributors[0]);
    ko.applyBindings(new ProjectViewModel(), $("#projectScope")[0]);

    // Clear user search modal when dismissed; catches dismiss by escape key
    // or cancel button.
    $addContributors.on('hidden', function() {
        viewModel.clear();
    });

    $("#browser").treeview();  // Initiate filebrowser



    ////////////////////
    // Event Handlers //
    ////////////////////

    $('.user-quickedit').hover(
        function(){
            me = $(this);
            el = $('<i class="icon-remove"></i>');
            el.click(function(){
                NodeActions.removeUser(me.attr("data-userid"), me.attr("data-fullname"));
                return false;
            });
            $(this).append(el);
        },
        function(){
            $(this).find("i").remove();
        }
    );

    /* Modal Click handlers for project page */

    // Private Button confirm dlg
    $('#privateButton').on('click', function() {
        var url = $(this).data("target");
        bootbox.confirm(Messages.makePrivateWarning,
            function(result) {
                if (result) {
                    $.ajax({
                        url: url,
                        type: "POST",
                        data: {"permissions": "public"},
                        contentType: "application/json",
                        dataType: "json",
                        success: function(data){
                            window.location.href = data["redirect_url"];
                        }
                    })
                }
            }
        )
    });

    // TODO(sloria): Repetition here. Rethink.
    // Public Button confirm dlg
    $('#publicButton').on('click', function() {
        var url = $(this).data("target");
        bootbox.confirm(Messages.makePublicWarning,
            function(result) {
                if (result) {
                    $.ajax({
                        url: url,
                        type: "POST",
                        data: {"permissions": "private"},
                        contentType: "application/json",
                        dataType: "json",
                        success: function(data){
                            window.location.href = data["redirect_url"];
                        }
                    })
                }
            }
        )
    });

})

}).call(this);

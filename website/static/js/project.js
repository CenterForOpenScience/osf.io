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

/* Utility functions */

/**
 * Return the id of the current node by parsing the current URL.
 */
window.nodeToUse = function(){
  if(location.pathname.match("\/project\/.*\/node\/.*")){
    return location.pathname.match("\/project\/.*?\/node\/(.*?)\/.*")[1];
  }else{
    return location.pathname.match("\/project\/(.*?)\/.*")[1];
  }
}


/**
 * Return the api url for the current node by parsing the current URL.
 */
window.nodeToUseUrl = function(){
    try{
        if (location.pathname.match("\/project\/.*\/node\/.*")) {
            return '/api/v1' + location.pathname.match("(\/project\/.*?\/node\/.*?)\/.*")[1] + "/";
        } else {
            return '/api/v1' + location.pathname.match("(\/project\/.*?)\/.*")[1] + "/";
        }
    } catch(err) {
        return undefined;
    }
}


window.NodeActions = {};  // Namespace for NodeActions
// TODO: move me to the ProjectViewModel
NodeActions.forkNode = function(){
    $.ajax({
        url: nodeToUseUrl() + "fork/",
        type: "POST",
    }).done(function(response) {
        window.location = response;
    });
};

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
                url: nodeToUseUrl() + "removecontributors/",
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
                console.log(response);
                logs.html(response);
                NodeActions._openCloseNode(node_id);
            }
        );
    } else {
        NodeActions._openCloseNode(node_id);
    }
};


$(document).ready(function() {

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
    // TODO(sloria): Move these to the ProjectViewModel
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

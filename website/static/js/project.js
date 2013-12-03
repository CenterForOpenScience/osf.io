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
};

/* Utility functions */

/**
 * Return the id of the current node by parsing the current URL.
 */
window.nodeToUse = function(){
    var match;
    match = location.pathname.match("\/project\/.*?\/node\/(.*?)\/.*");
    if (match)
        return match[1];
    match = location.pathname.match("\/project\/(.*?)\/.*");
    if (match)
        return match[1];
    return undefined;
};


/**
 * Return the api url for the current node by parsing the current URL.
 */
window.nodeToUseUrl = function(){
    var match;
    match = location.pathname.match("(\/project\/.*?\/node\/.*?)\/.*");
    if (match)
        return '/api/v1' + match[1] + '/';
    match = location.pathname.match("(\/project\/.*?)\/.*");
    if (match)
        return '/api/v1' + match[1] + '/';
    return undefined;
};

window.block = function() {
    $.blockUI({
        css: {
            border: 'none',
            padding: '15px',
            backgroundColor: '#000',
            '-webkit-border-radius': '10px',
            '-moz-border-radius': '10px',
            opacity: .5,
            color: '#fff'
        },
        message: 'Please wait'
    });
};

window.NodeActions = {};  // Namespace for NodeActions
// TODO: move me to the ProjectViewModel
NodeActions.forkNode = function(){

    // Block page
    block();

    // Fork node
    $.ajax({
        url: nodeToUseUrl() + 'fork/',
        type: 'POST'
    }).done(function(response) {
        window.location = response;
    }).fail(function() {
        $.unblockUI();
        bootbox.alert('Forking failed');
    });

};

// todo: discuss; this code not used
NodeActions.addNodeToProject = function(node, project) {
    $.ajax({
        url: '/project/' + project + '/addnode/' + node,
        type: 'POST',
        data: 'node=' + node + '&project=' + project
    }).done(function(msg) {
        var $node = $('#node' + node);
        $node.removeClass('primary').addClass('success');
        $node.onclick = function(){};
        $node.html('Added');
    });
};

$(function(){
    $('#newComponent form').on('submit', function(e) {
          e.preventDefault();

          $("#add-component-submit")
              .attr("disabled", "disabled")
              .text("Adding");

          if ($.trim($("#title").val())==''){

              $("#alert").text("The new component title cannot be empty");

              $("#add-component-submit")
                      .removeAttr("disabled","disabled")
                      .text("OK");
          }
          else if ($(e.target).find("#title").val().length>200){
              $("#alert").text("The new component title cannot be more than 200 characters.");

              $("#add-component-submit")
                      .removeAttr("disabled","disabled")
                      .text("OK");
          }
          else{
              $.ajax({
                   url: $(e.target).attr("action"),
                   type:"POST",
                   timeout:60000,
                   data:$(e.target).serialize()
              }).success(function(){
                  location.reload();
              }).fail(function(jqXHR, textStatus, errorThrown){
                    if(textStatus==="timeout") {
                        $("#alert").text("Add component timed out"); //Handle the timeout
                    }else{
                        $("#alert").text('Add component failed');
                    }
                    $("#add-component-submit")
                      .removeAttr("disabled","disabled")
                      .text("OK");
              });
          }
     });
});

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
};

/*
Display recent logs for for a node on the project view page.
*/
NodeActions.openCloseNode = function(node_id){
    var $logs = $('#logs-' + node_id);
    if (!$logs.hasClass("active")) {
        if (!$logs.hasClass("served")) {
            $.getJSON(
                $logs.attr('data-uri'),
                {count: 3},
                function(response) {
                    var logModelObjects = createLogs(response["logs"]);
                    var logsVM = new LogsViewModel(logModelObjects);
                    ko.applyBindings(logsVM, $logs[0]);
                    $logs.addClass("served")
                }
            );
        };
        $logs.addClass("active");
    } else {
        $logs.removeClass("active");
    }
    // Hide/show the html
    NodeActions._openCloseNode(node_id);
};


$(document).ready(function() {

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

});

}).call(this);

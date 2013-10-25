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

var nodeToUse = function(){
  if(location.pathname.match("\/project\/.*\/node\/.*")){
    return location.pathname.match("\/project\/.*?\/node\/(.*?)\/.*")[1];
  }else{
    return location.pathname.match("\/project\/(.*?)\/.*")[1];
  }
}

var nodeToUseUrl = function(){
  if (location.pathname.match("\/project\/.*\/node\/.*")) {
    return '/api/v1' + location.pathname.match("(\/project\/.*?\/node\/.*?)\/.*")[1];
  } else {
    return '/api/v1' + location.pathname.match("(\/project\/.*?)\/.*")[1];
  }
}

var setStatus = function(status){
    $('#alert-container').append(status);//'<div class=\'alert-message warning fade in\' data-alert=\'alert\'><a class=\'close\' href=\'#\'>&times;</a><p>'+ status +'</p></div>');
};

var urlDecode = function(str) {
    return decodeURIComponent((str+'').replace(/\+/g, '%20'));
}


/**
 * Display a modal confirmation window before relocating to an url.
 * @param  <String> message
 * @param  <String> url
 */
var modalConfirm = function(message, url){
    bootbox.confirm(message,
        function(result) {
            if (result) {
                window.location.href = url;
            }
        }
    )
}

window.NodeActions = {};  // Namespace for NodeActions

NodeActions.forkNode = function(){
    $.ajax({
        url: nodeToUseUrl() + "/fork/",
        type: "POST",
    }).done(function(response) {
        window.location = response;
    });
};

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

$(document).ready(function(){

    $('.nav a[href="' + location.pathname + '"]').parent().addClass('active');
    $('.tabs a[href="' + location.pathname + '"]').parent().addClass('active');

    $('#tagitfy').tagit({
              availableTags: ["analysis", "methods", "introduction", "hypotheses"], // this param is of course optional. it's for autocomplete.
              // configure the name of the input field (will be submitted with form), default: item[tags]
              fieldName: 'tags',
              singleField: true
    });

    $("[rel=tooltip]").tooltip({
        placement:'bottom',
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


});

/////////////////////
// Project JS      //
/////////////////////
(function(){

// Messages, e.g. for confirmation dialogs, alerts, etc.
var Messages = {
    makePublicWarning: 'Once a project is made public, there is no way to guarantee that ' +
                        'access to the data it contains can be complete prevented. Users ' +
                        'should assume that once a project is made public, it will always ' +
                        'be public. Are you absolutely sure you would like to continue?',

    makePrivateWarning: 'Making a project private will prevent users from viewing it on this site, ' +
                        'but will have no impact on external sites, including Google\'s cache. ' +
                        'Would you like to continue?'
};

/* Utility functions */

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

window.unblock = function() {
    $.unblockUI();
};

window.joinPrompts = function(prompts, base) {
    var prompt = base || '';
    if (prompts) {
        prompt += '<hr />';
        prompt += '<ul>';
        for (var i=0; i<prompts.length; i++) {
            prompt += '<li>' + prompts[i] + '</li>';
        }
        prompt += '</ul>';
    }
    return prompt;
}

window.NodeActions = {};  // Namespace for NodeActions
// TODO: move me to the ProjectViewModel

NodeActions.beforeForkNode = function() {

    $.ajax({
        url: nodeApiUrl + 'beforefork/',
        contentType: 'application/json'
    }).success(function(response) {
        bootbox.confirm(
            joinPrompts(response.prompts, 'Are you sure you want to fork this project?'),
            function(result) {
                if (result) {
                    NodeActions.forkNode();
                }
            }
        )
    });

};

NodeActions.forkNode = function() {

    // Block page
    block();

    // Fork node
    $.ajax({
        url: nodeApiUrl + 'fork/',
        type: 'POST'
    }).done(function(response) {
        window.location = response;
    }).fail(function() {
        unblock();
        bootbox.alert('Forking failed');
    });

};

// todo: discuss; this code not used
NodeActions.addNodeToProject = function(node, project) {
    $.ajax({
        url: '/' + project + '/addnode/' + node,
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

    $(".remove-private-link").on("click",function(){
        var me = $(this);
        var data_to_send={
            'private_link': me.attr("data-link")
        };
        bootbox.confirm('Are you sure to remove this private link?', function(result) {
            if (result) {
                $.ajax({
                    type: "POST",
                    url: nodeApiUrl + "removePrivateLink/",
                    contentType: "application/json",
                    dataType: "json",
                    data: JSON.stringify(data_to_send)
                }).done(function(response) {
                    window.location.reload();
                });
            }
         });
    });

    $('#newComponent form').on('submit', function(e) {

          $("#add-component-submit")
              .attr("disabled", "disabled")
              .text("Adding");

          if ($.trim($("#title").val())==''){

              $("#alert").text("The new component title cannot be empty");

              $("#add-component-submit")
                      .removeAttr("disabled","disabled")
                      .text("OK");

              e.preventDefault();
          }
          else if ($(e.target).find("#title").val().length>200){
              $("#alert").text("The new component title cannot be more than 200 characters.");

              $("#add-component-submit")
                      .removeAttr("disabled","disabled")
                      .text("OK");

              e.preventDefault();

          }
//          else{
//              $.ajax({
//                   url: $(e.target).attr("action"),
//                   type:"POST",
//                   timeout:60000,
//                   data:$(e.target).serialize()
//              }).success(function(){
//                  location.reload();
//              }).fail(function(jqXHR, textStatus, errorThrown){
//                    if(textStatus==="timeout") {
//                        $("#alert").text("Add component timed out"); //Handle the timeout
//                    }else{
//                        $("#alert").text('Add component failed');
//                    }
//                    $("#add-component-submit")
//                      .removeAttr("disabled","disabled")
//                      .text("OK");
//              });
//          }

     });
});

NodeActions.removeUser = function(userid, name) {
    var data = JSON.stringify({
        id: userid,
        name: name
    });
    $.ajax({
        type: 'POST',
        url: nodeApiUrl + 'beforeremovecontributors/',
        contentType: 'application/json',
        dataType: 'json',
        data: data
    }).success(function(response) {
        var prompt = joinPrompts(response.prompts, 'Remove ' + name + ' from contributor list?');
        bootbox.confirm(prompt, function(result) {
            if (result) {
                $.ajax({
                    type: 'POST',
                    url: nodeApiUrl + 'removecontributors/',
                    contentType: 'application/json',
                    dataType: 'json',
                    data: data
                }).done(function(response) {
                    window.location.reload();
                });
            }
        });
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
        }
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

    $('.citation-toggle').on('click', function() {
        $(this).closest('.citations').find('.citation-list').slideToggle();
    });

    $('.user-quickedit').hover(
        function(){
            var me = $(this);
            var el = $('<i class="icon-remove"></i>');
            el.click(function(){
                NodeActions.removeUser(me.attr('data-userid'), me.attr('data-fullname'));
                return false;
            });
            $(this).append(el);
        },
        function(){
            $(this).find('i').remove();
        }
    );

    function setPermissions(url, permissions) {
        var msgKey = permissions == 'public' ?
            'makePublicWarning' :
            'makePrivateWarning';
        bootbox.confirm(
            Messages[msgKey],
            function(result) {
                if (result) {
                    $.ajax({
                        url: url,
                        type: 'POST',
                        data: {permissions: permissions},
                        contentType: 'application/json',
                        dataType: 'json',
                        success: function(data){
                            window.location.href = data['redirect_url'];
                        }
                    });
                }
            }
        );
    }

    /* Modal Click handlers for project page */
    // TODO(sloria): Move these to the ProjectViewModel
    // Private Button confirm dlg
    $('#privateButton').on('click', function() {
        var url = $(this).data("target");
        setPermissions(url, 'private');
    });

    // Public Button confirm dlg
    $('#publicButton').on('click', function() {
        var url = $(this).data("target");
        setPermissions(url, 'public');
    });

    // Widgets

    $('.widget-disable').on('click', function() {

        var $this = $(this);

        $.ajax({
            url: $this.attr('href'),
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            complete: function() {
                window.location = '/' + nodeId + '/';
            }
        });

        return false;

    });

});

}).call(this);

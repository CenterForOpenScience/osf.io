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

// TODO: Shouldn't pollute window. At the very least put them on the '$' namespace
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
};

window.NodeActions = {};  // Namespace for NodeActions
// TODO: move me to the ProjectViewModel

function beforeForkNode(url, done) {

    $.ajax({
        url: url,
        contentType: 'application/json'
    }).success(function(response) {
        bootbox.confirm(
            joinPrompts(response.prompts, 'Are you sure you want to fork this project?'),
            function(result) {
                if (result) {
                    done && done();
                }
            }
        )
    });

}

NodeActions.forkNode = function() {

    beforeForkNode(nodeApiUrl + 'fork/before/', function() {

        // Block page
        block();

        // Fork node
        $.ajax({
            url: nodeApiUrl + 'fork/',
            type: 'POST'
        }).success(function(response) {
            window.location = response;
        }).error(function() {
            unblock();
            bootbox.alert('Forking failed');
        });

    });

};

NodeActions.forkPointer = function(pointerId, nodeId) {

    beforeForkNode('/api/v1/' + nodeId + '/fork/before/', function() {

        // Block page
        block();

        // Fork pointer
        $.ajax({
            type: 'post',
            url: nodeApiUrl + 'pointer/fork/',
            data: JSON.stringify({'pointerId': pointerId}),
            contentType: 'application/json',
            dataType: 'json',
            success: function(response) {
                window.location.reload();
            },
            error: function() {
                unblock();
                bootbox.alert('Could not fork link.');
            }
        });

    });

};


NodeActions.addonFileRedirect = function(item) {
    window.location.href = item.params.urls.view;
    return false;
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
        var prompt = joinPrompts(response.prompts, 'Remove <strong>' + name + '</strong> from contributor list?');
        bootbox.confirm({
            title: 'Delete Contributor?',
            message: prompt,
            callback: function(result) {
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
            }
        });
    });
    return false;
};

NodeActions._openCloseNode = function(nodeId) {

    var icon = $('#icon-' + nodeId);
    var body = $('#body-' + nodeId);

    body.toggleClass('hide');

    if ( body.hasClass('hide') ) {
        icon.removeClass('icon-minus');
        icon.addClass('icon-plus');
        icon.attr('title', 'More');
    } else {
        icon.removeClass('icon-plus');
        icon.addClass('icon-minus');
        icon.attr('title', 'Less');
    }

    // Refresh tooltip text
    icon.tooltip('destroy');
    icon.tooltip();

};


NodeActions.reorderChildren = function(idList, elm) {
    $.ajax({
        type: 'POST',
        url: nodeApiUrl + 'reorder_components/',
        data: JSON.stringify({'new_list': idList}),
        contentType: 'application/json',
        dataType: 'json',
        fail: function() {
            $(elm).sortable('cancel');
        }
    });
};

NodeActions.removePointer = function(pointerId, pointerElm) {
    $.ajax({
        type: 'DELETE',
        url: nodeApiUrl + 'pointer/',
        data: JSON.stringify({pointerId: pointerId}),
        contentType: 'application/json',
        dataType: 'json',
        success: function(response) {
            pointerElm.remove();
        }
    })
};

/*
refresh rendered file through mfr
*/

window.FileRenderer = {
    start: function(url, selector){
        this.url = url;
        this.element = $(selector);
        this.tries = 0;
        this.refreshContent = window.setInterval(this.getCachedFromServer.bind(this), 1000);
    },

    getCachedFromServer: function() {
        var self = this;
        $.get( self.url, function(data) {
            if (data) {
                self.element.html(data);
                clearInterval(self.refreshContent);
            } else {
                self.tries += 1;
                if(self.tries > 10){
                    clearInterval(self.refreshContent);
                    self.element.html("Timeout occurred while loading, please refresh the page")
                }
            }
        });
     }
};

/*
Display recent logs for for a node on the project view page.
*/
NodeActions.openCloseNode = function(nodeId){
    var $logs = $('#logs-' + nodeId);
    if (!$logs.hasClass('active')) {
        if (!$logs.hasClass('served')) {
            $.getJSON(
                $logs.attr('data-uri'),
                {count: 3},
                function(response) {
                    var logModelObjects = createLogs(response.logs);
                    var logsVM = new LogsViewModel(logModelObjects);
                    ko.applyBindings(logsVM, $logs[0]);
                    $logs.addClass('served');
                }
            );
        }
        $logs.addClass('active');
    } else {
        $logs.removeClass('active');
    }
    // Hide/show the html
    NodeActions._openCloseNode(nodeId);
};


$(document).ready(function() {

    ////////////////////
    // Event Handlers //
    ////////////////////

    $('.remove-pointer').on('click', function() {
        var $this = $(this);
        bootbox.confirm(
            'Are you sure you want to remove this link? This will not ' +
            'remove the project this link refers to.',
            function(result) {
                if (result) {
                    var pointerId = $this.attr('data-id');
                    var pointerElm = $this.closest('.list-group-item');
                    NodeActions.removePointer(pointerId, pointerElm);
                }
            }
        )
    });

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
        bootbox.confirm({
            title: "Warning",
            message: Messages[msgKey],
            callback: function(result) {
                if (result) {
                    $.postJSON(url, {permissions: permissions},
                        function(data){
                            window.location.href = data.redirect_url;
                        }
                    );
                }
            }
        });
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

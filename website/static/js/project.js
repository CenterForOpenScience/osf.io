/////////////////////
// Project JS      //
/////////////////////
(function($){

/* Utility functions */


window.NodeActions = {};  // Namespace for NodeActions

// TODO: move me to the ProjectViewModel
NodeActions.forkPointer = function(pointerId, nodeId) {

    beforeForkNode('/api/v1/' + nodeId + '/fork/before/', function() {

        // Block page
        $.osf.block();

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

}).call(this, jQuery);

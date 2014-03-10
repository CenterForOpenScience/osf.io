/////////////////////
// Project JS      //
/////////////////////
(function($){



window.NodeActions = {};  // Namespace for NodeActions


// TODO: move me to the NodeControl or separate
    NodeActions.forkPointer = function(pointerId, nodeId) {
        bootbox.confirm('Are you sure you want to fork this project?',
                function(result) {
                    if (result) {
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
                                $.osf.unblock();
                                bootbox.alert('Could not fork link.');
                            }
                        });
                    }
                }
        )
    };

NodeActions.addonFileRedirect = function(item) {
    window.location.href = item.params.urls.view;
    return false;
};

NodeActions.useAsTemplate = function() {
    $.osf.block();

    $.ajax({
        url: '/api/v1/project/new/' + nodeId + '/',
        type: 'POST',
        dataType: 'json',
        success: function(data) {
            window.location = data['url']
        },
        fail: function() {
            $.osf.unblock();
            bootbox.alert('Templating failed');
        }
    });
}

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
                    $script(['/static/js/logFeed.js'], function() {
                        var log = new LogFeed($logs, response.logs);
                    });
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

    ko.punches.enableAll();

    var permissionInfoHtml = '<ul>' +
            '<li><strong>Read</strong>: View project content and comment</li>' +
            '<li><strong>Read + Write</strong>: Read privileges plus add and configure components; add and edit content</li>' +
            '<li><strong>Administrator</strong>: Read and write privileges; manage contributors; delete and register project; public-private settings</li>' +
        '</ul>';

    $('.permission-info').attr(
        'data-content', permissionInfoHtml
    ).popover();

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

/////////////////////
// Project JS      //
/////////////////////
(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'js/logFeed', 'osfutils'], factory);
    } else {
        factory(jQuery, global.LogFeed);
    }
}(this, function($, LogFeed) {

window.NodeActions = {};  // Namespace for NodeActions

// TODO: move me to the NodeControl or separate module
NodeActions.beforeForkNode = function(url, done) {
    $.ajax({
        url: url,
        contentType: 'application/json'
    }).success(function(response) {
        bootbox.confirm(
             $.osf.joinPrompts(response.prompts, 'Are you sure you want to fork this project?'),
             function(result) {
                 if (result) {
                     done && done();
                 }
             }
         );
    });
};

NodeActions.forkNode = function() {
    NodeActions.beforeForkNode(nodeApiUrl + 'fork/before/', function() {
        // Block page
        $.osf.block();
        // Fork node
        $.ajax({
            url: nodeApiUrl + 'fork/',
            type: 'POST'
        }).success(function(response) {
            window.location = response;
        }).error(function() {
            $.osf.unblock();
            bootbox.alert('Forking failed');
        });
    });
};

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
        error: function(response) {
            $.osf.unblock();
            $.osf.handleJSONError(response);
        }
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
        error: function(response) {
            $(elm).sortable('cancel');
            $.osf.handleJSONError(response);
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
                    var log = new window.LogFeed($logs, response.logs);
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

    var permissionInfoHtml = '<dl>' +
            '<dt>Read</dt><dd>View project content and comment</dd>' +
            '<dt>Read + Write</dt><dd>Read privileges plus add and configure components; add and edit content</dd>' +
            '<dt>Administrator</dt><dd>Read and write privileges; manage contributors; delete and register project; public-private settings</dd>' +
        '</dl>';

    $('.permission-info').attr(
        'data-content', permissionInfoHtml
    ).popover();

    var visibilityInfoHtml = 'Only visible contributors will be displayed ' +
        'in the Contributors list and in project citations. Non-visible ' +
        'contributors can read and modify the project as normal.';

    $('.visibility-info').attr(
        'data-content', visibilityInfoHtml
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

    $('body').on('click', '.tagsinput .tag > span', function(e) {
        window.location = "/search/?q=" + $(e.target).text().toString().trim();
    });

    $('.citation-toggle').on('click', function(evt) {
        $(this).closest('.citations').find('.citation-list').slideToggle();
        return false;
    });

});

}));

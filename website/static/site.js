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


window.NodeActions = {};  // Namespace for NodeActions

NodeActions.forkNode = function(){
  $.ajax({
    url: nodeToUseUrl() + "/fork/",
    type:"POST",
  }).done(function(response){
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

NodeActions.removeUser = function(userid, name, el){
    var answer = confirm("Remove " + name + " from contributor list?")
    if (answer){
        $.ajax({
            type: "POST",
            url: nodeToUseUrl() + "/removecontributors/",
            contentType: "application/json",
            dataType: "json",
            data: JSON.stringify({"id": userid, "name":name}),
        }).done(function(response){
                window.location.reload();
            });

    }
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

/*
Adds yes/no confirmation modals, using Bootstrap.

To use, place a [data-confirm='<Your confirmation message>'] on any link.

Examples
=========

Simple:
<a href='/logout' data-confirm='Are you sure you want to log out?'>Log Out</a>

With a modal window title specified:
<a href='/delete_everything/' data-confirm='Are you really sure you want to delete everything?' data-confirm-title='DANGER!'>Delete it all</a></li>

Supported Attributes
====================

data-confirm:
    (required) Value used for the body of the confirmation window.

data-confirm-title:
    The title of the modal. Default is "Are you sure?"

data-confirm-yes:
    The title of the "Yes" button.

data-confirm-no:
    The title of the "No" button.



 */
function generateConfirmModal(args) {
    // Supported parameters
    var params = ['message','title','confirm_text','deny_text'];

    if(typeof(args) == 'string') {
        // A single string was passed, assume it was a message body
        params.message = args
    } else if(typeof(args) == 'object') {
        // An object was passed, use it to override defaults
        for(var i = 0; i<params.length; i++) {
            if(typeof(args[params[i]]) !== 'undefined') {
                // If the param was passed, override the default
                params[params[i]] = args[params[i]]
            }
        }
    }
    var template = [
        '<div class="modal hide fade">',
            '<div class="modal-header">',
                '<button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>',
                '<h3>Are you sure?</h3>',
            '</div>',
            '<div class="modal-body">',
                '<p></p>',
            '</div>',
            '<div class="modal-footer">',
                '<button href="#" data-dismiss="modal" class="btn modal-deny">No</button>',
                '<button href="#" data-dismiss="modal" class="btn btn-primary modal-confirm">Yes</button>',
            '</div>',
        '</div>'
    ].join('');

    // If document.modals doesn't exist, create it as an empty array.
    if( typeof(document.modals) === 'undefined' ) {
        document.modals = [];
    };

    params.id = 'modal_' + document.modals.length.toString()

    // Apply passed params to the template
    var modal = $(template).attr('id', params.id);
    modal.find('h3').text(params.title);
    modal.find('.modal-body > p').text(params.message);
    modal.find('.modal-deny').text(params.deny_text);
    modal.find('.modal-confirm').text(params.confirm_text);


    // Store which button is clicked so a callback can find it.
    $(modal).find('.modal-confirm, .modal-deny').on('click', function(){
       if( $(this).hasClass('modal-confirm') ) {
           $(this).parents('.modal').attr('data-result', 1);
       } else if( $(this).hasClass('modal-deny') ) {
           $(this).parents('.modal').attr('data-result', 0);
       }
    });

    document.modals.push(modal);
    $(document.body).append(modal);
    return '#' + params.id
};

$(function(){
    // map HTML attributes to JS params
    var data_params = [
        ['data-confirm','message'],
        ['data-confirm-title', 'title'],
        ['data-confirm-yes', 'confirm_text'],
        ['data-confirm-no', 'deny_text'],
    ];

    $('[data-confirm]').each(function(index) {
        // for each modal-enabled link
        var modal_args = {};

        // build param list
        for(var i = 0; i < data_params.length; i++ ){

            var key = data_params[i];
            if(typeof($(this).attr(key[0])) !== 'undefined') {

                // If the param was passed, override the default
                modal_args[key[1]] = $(this).attr(key[0]);

            };

        };


        var modal_id = generateConfirmModal(modal_args);

        // Attach the modal's ID
        $(this).attr('data-modal', modal_id);

        $(this).on('click', function() {
            var href = $(this).attr('href');
            // Set up the callback
            $(modal_id).one('hidden', function() {
                var result = $(this).attr('data-result');
                $(this).removeAttr('data-result');
                if( result == '1' ){
                    window.location = href;
                };
            });

            // Show the modal
            $(modal_id).modal('show');

            // Suppress the default link behavior
            return false;
        });


    });
});

$(document).ready(function(){

    $('.nav a[href="' + location.pathname + '"]').parent().addClass('active');
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

    $('.user-quickedit').hover(
        function(){
            me = $(this);
            el = $('<i class="icon-remove"></i>');
            el.click(function(){
                NodeActions.removeUser(me.attr("data-userid"), me.attr("data-fullname"), me);
                return false;
            });
            $(this).append(el);
        },
        function(){
            $(this).find("i").remove();
        }
    );

    $("#browser").treeview();
});

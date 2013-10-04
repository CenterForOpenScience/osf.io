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

NodeActions.watchNode = function() {
    // Send POST request to node's watch API url and update the watch count
    $.ajax({
        url: nodeToUseUrl() + "/watch/",
        type: "POST",
        dataType: "json",
        success: function(data, status, xhr) {
            $watchCount = $("#watchCount");
            $watchCount.html("Unwatch&nbsp;" + data["watchCount"]);
        }
    });
}

NodeActions.unwatchNode = function () {
    // Send POST request to node's watch API url and update the watch count
    $.ajax({
        url: nodeToUseUrl() + "/unwatch/",
        type: "POST",
        dataType: "json",
        success: function(data, status, xhr) {
            $watchCount = $("#watchCount");
            $watchCount.html("Watch&nbsp;" + data["watchCount"]);
        }
    });
}

var addNodeToProject = function(node, project){
    $.ajax({
       url:"/project/" + project + "/addnode/" + node,
       type:"POST",
       data:"node="+node+"&project="+project}).done(function(msg){
           $('#node'+node).removeClass('primary').addClass('success');
           $('#node'+node).onclick = function(){};
           $('#node'+node).html('Added');
       });
};

var removeUser = function(userid, name, el){
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
                removeUser(me.attr("data-userid"), me.attr("data-fullname"), me);
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

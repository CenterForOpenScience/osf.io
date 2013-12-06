//////////////////
// Site-wide JS //
//////////////////
(function() {


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
};
$(document).ready(function(){
    //block the create new project button when the form is submitted
    $('#projectForm').on('submit',function(){
        $('button[type="submit"]', this)
            .attr('disabled', 'disabled')
            .text('Creating');
    });

    // Highlight active tabs and nav labels
    if (typeof(nodeId) !== 'undefined' && nodeId) {
        // Works for project pages; code used below won't highlight wiki tab
        // on wiki pages because URLs (e.g. wiki/home) aren't contained in
        // tab URLs (e.g. wiki)
        var page = location.pathname.split(nodeId)[1]
            .split('/')[1];
        $('#projectSubnav a').filter(function() {
            return page == $(this).attr('href')
                .split(nodeId)[1]
                .replace(/\//g, '');
        }).parent().addClass('active');
    } else {
         // Works for user dashboard page
         $('.nav a[href="' + location.pathname + '"]').parent().addClass('active');
         $('.tabs a[href="' + location.pathname + '"]').parent().addClass('active');
    }

    // Initiate tag input
    $('#tagitfy').tagit({
              availableTags: ["analysis", "methods", "introduction", "hypotheses"], // this param is of course optional. it's for autocomplete.
              // configure the name of the input field (will be submitted with form), default: item[tags]
              fieldName: 'tags',
              singleField: true
    });

    // Build tooltips on user activity widgets
    $('.ua-meter').tooltip();
    $("[rel=tooltip]").tooltip({
        placement:'bottom'
    });

    //  Initiate tag cloud (on search page)
    $.fn.tagcloud.defaults = {
      size: {start: 14, end: 18, unit: 'pt'},
      color: {start: '#cde', end: '#f52'}
    };

    $(function () {
      $('#whatever a').tagcloud();
    });


});

}).call(this);

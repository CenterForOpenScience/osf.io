////////////////////////////
// Site-wide JS utilities //
////////////////////////////
(function($, global) {

// Namespace to put utility functions on
$.osf = {};

// TODO: should probably add namespace to these, e.g. $.osf.postJSON
/**
 * Posts JSON data.
 *
 * Example:
 *     $.postJSON('/foo', {'email': 'bar@baz.com'}, function(data) {...})
 *
 * @param  {String} url  The url to post to
 * @param  {Object} data JSON data to send to the endpoint
 * @param  {Function} done Success callback. Takes returned data as its first argument
 * @return {jQuery xhr}
 */
// TODO: backwards compatible with un-namespaced function. eventually remove
$.postJSON = $.osf.postJSON = function(url, data, done) {
    var ajaxOpts = {
        url: url, type: 'post',
        data: JSON.stringify(data),
        success: done,
        contentType: 'application/json', dataType: 'json'
    };
    return $.ajax(ajaxOpts);
};

/**
 * Get a URL parameter by name.
 *
 * https://stackoverflow.com/questions/901115/how-can-i-get-query-string-values-in-javascript
 */
// TODO: backwards compatible with un-namespaced function. eventually remove
$.urlParam = $.osf.urlParam = function(name) {
    name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
};

// TODO: attaches to global for backwards-compatibility. Eventually remove.
global.block = $.osf.block = function() {
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

global.unblock = $.osf.unblock = function() {
    $.unblockUI();
};

global.joinPrompts = function(prompts, base) {
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


LOCAL_DATEFORMAT = "l h:mm A";
UTC_DATEFORMAT = "l H:mm UTC";

/**
 * A date object with two formats: local time or UTC time.
 * @param {String} date The original date as a string. Should be an standard
 *                      format such as RFC or ISO.
 */
global.FormattableDate = function(date) {
    this.date = date;
    this.local = moment(date).format(LOCAL_DATEFORMAT);
    this.utc = moment.utc(date).format(UTC_DATEFORMAT);
}


// TODO: move me to appropriate page-specific module
$(document).ready(function(){
    //block the create new project button when the form is submitted
    $('#projectForm').on('submit',function(){
        $('button[type="submit"]', this)
            .attr('disabled', 'disabled')
            .text('Creating');
    });

//    TODO: Make this work with file GUIDs [jmc]
//    // Highlight active tabs and nav labels
//    if (typeof(nodeId) !== 'undefined' && nodeId) {
//        // Works for project pages; code used below won't highlight wiki tab
//        // on wiki pages because URLs (e.g. wiki/home) aren't contained in
//        // tab URLs (e.g. wiki)
//        var page = location.pathname.split(nodeId)[1]
//            .split('/')[1];
//        $('#projectSubnav a').filter(function() {
//            return page == $(this).attr('href')
//                .split(nodeId)[1]
//                .replace(/\//g, '');
//        }).parent().addClass('active');
//    } else {
//         // Works for user dashboard page
//         $('.nav a[href="' + location.pathname + '"]').parent().addClass('active');
//         $('.tabs a[href="' + location.pathname + '"]').parent().addClass('active');
//    }

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
      $('#tagCloud a').tagcloud();
    });


});

}).call(this, jQuery, window);

////////////////////////////
// Site-wide JS utilities //
////////////////////////////
(function($, global) {

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
$.postJSON = function(url, data, done) {
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
$.urlParam = function(name) {
    name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
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


// TODO: this should be in project.js
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

    $(function () {  // TODO: remove?
      $('#whatever a').tagcloud();
    });


});

}).call(this, jQuery, window);

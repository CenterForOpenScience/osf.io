////////////////////////////
// Site-wide JS utilities //
////////////////////////////
(function($, global) {
    'use strict';

    // Namespace to put utility functions on
    $.osf = {};

    /**
     * Posts JSON data.
     *
     * Example:
     *     $.osf.postJSON('/foo', {'email': 'bar@baz.com'}, function(data) {...})
     *
     * @param  {String} url  The url to post to
     * @param  {Object} data JSON data to send to the endpoint
     * @param  {Function} done Success callback. Takes returned data as its first argument
     * @return {jQuery xhr}
     */
    $.osf.postJSON = function(url, data, done) {
        var ajaxOpts = {
            url: url, type: 'post',
            data: JSON.stringify(data),
            success: done,
            contentType: 'application/json', dataType: 'json'
        };
        return $.ajax(ajaxOpts);
    };

    /**
     * Puts JSON data.
     *
     * Example:
     *     $.osf.putJSON('/foo', {'email': 'bar@baz.com'}, function(data) {...})
     *
     * @param  {String} url  The url to put to
     * @param  {Object} data JSON data to send to the endpoint
     * @param  {Function} done Success callback. Takes returned data as its first argument
     * @return {jQuery xhr}
     */
    $.osf.putJSON = function(url, data, done) {
        var ajaxOpts = {
            url: url, type: 'put',
            data: JSON.stringify(data),
            success: done,
            contentType: 'application/json', dataType: 'json'
        };
        return $.ajax(ajaxOpts);
    };

    $.osf.block = function() {
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

    $.osf.unblock = function() {
        $.unblockUI();
    };

    $.osf.joinPrompts = function(prompts, base) {
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

    $.osf.mapByProperty = function(list, attr) {
        return $.map(list, function(item) {
            return item[attr];
        });
    };


    /**
     * Return whether or not a value is an email address.
     * Adapted from Knockout-Validation.
     */
    $.osf.isEmail = function(value) {
        return  /^((([a-z]|\d|[!#\$%&'\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+(\.([a-z]|\d|[!#\$%&'\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+)*)|((\x22)((((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(([\x01-\x08\x0b\x0c\x0e-\x1f\x7f]|\x21|[\x23-\x5b]|[\x5d-\x7e]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(\\([\x01-\x09\x0b\x0c\x0d-\x7f]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]))))*(((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(\x22)))@((([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.)+(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))$/i.test(value);
    };

    var LOCAL_DATEFORMAT = 'l h:mm A';
    var UTC_DATEFORMAT = 'l H:mm UTC';

    /**
     * A date object with two formats: local time or UTC time.
     * @param {String} date The original date as a string. Should be an standard
     *                      format such as RFC or ISO.
     */
    global.FormattableDate = function(date) {
        this.date = date;
        this.local = moment(date).format(LOCAL_DATEFORMAT);
        this.utc = moment.utc(date).format(UTC_DATEFORMAT);
    };

    $.widget( "custom.catcomplete", $.ui.autocomplete, {
        _renderMenu: function( ul, items ) {
            var that = this;
            var currentCategory = "";
            $.each( items, function( index, item ) {
                if ( item.category != currentCategory ) {
                    ul.append( "<li class='ui-autocomplete-category'>" + item.category + "</li>" );
                    currentCategory = item.category;
                }
            that._renderItemData( ul, item );
            });
        }
    });


    // TODO: move me to appropriate page-specific module
    $(document).ready(function(){
        //block the create new project button when the form is submitted
        // TODO: make this a reuseable function.
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

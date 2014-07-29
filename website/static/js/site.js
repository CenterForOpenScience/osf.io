////////////////////////////
// Site-wide JS utilities //
////////////////////////////
(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'knockout', 'moment',
                'jquery-ui',
                'vendor/jquery-blockui/jquery.blockui',
                'vendor/knockout-sortable/knockout-sortable'], factory);
    } else {
        factory(jQuery, global.ko, global.moment);
    }
}(this, function($, ko, moment) {
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
    $.osf.postJSON = function(url, data, done, error) {
        var ajaxOpts = {
            url: url, type: 'post',
            data: JSON.stringify(data),
            success: done,
            error: error,
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
    $.osf.putJSON = function(url, data, done, error) {
        var ajaxOpts = {
            url: url, type: 'put',
            data: JSON.stringify(data),
            success: done,
            error: error,
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
                opacity: 0.5,
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

    /**
     * Get query string arguments as an object.
     * From getQueryParameters plugin by Nicholas Ortenzio.
     *
     */
    $.osf.urlParams = function(str) {
        return (str || document.location.search).replace(/(^\?)/,'').split('&')
            .map(function(n){return n = n.split('='),this[n[0]] = n[1],this;}.bind({}))[0];
    };

    ///////////
    // Piwik //
    ///////////

    $.osf.trackPiwik = function(host, siteId, cvars, useCookies) {
        cvars = Array.isArray(cvars) ? cvars : [];
        useCookies = typeof(useCookies) !== 'undefined' ? useCookies : false;
        try {
            var piwikTracker = Piwik.getTracker(host + 'piwik.php', siteId);
            piwikTracker.enableLinkTracking(true);
            for(var i=0; i<cvars.length;i++)
            {
                piwikTracker.setCustomVariable.apply(null, cvars[i]);
            }
            if (!useCookies) {
                piwikTracker.disableCookies();
            }
            piwikTracker.trackPageView();

        } catch(err) { return false; }
        return true;
    };

    //////////////////
    // Data binders //
    //////////////////

    /**
     * Tooltip data binder. The value accessor should be an object containing
     * parameters for the tooltip.
     * Example:
     * <span data-bind="tooltip: {title: 'Tooltip text here'}"></span>
     */
    ko.bindingHandlers.tooltip = {
        init: function(elem, valueAccessor) {
            $(elem).tooltip(valueAccessor());
        }
    };

    // Patch sortable binding handler to preserve table row widths on drag.
    // See https://github.com/rniemeyer/knockout-sortable/pull/46
    // This can be removed if/when above PR is merged
    ko.bindingHandlers.sortable.options.helper = function(e, ui) {
        ui.children().each(function() {
            $(this).width($(this).width());
        });
        return ui;
    };

    /**
     * A thin wrapper around ko.applyBindings that ensures that a view model
     * is bound to the expected element. Also shows the element if it was
     * previously hidden.
     *
     * Takes a ViewModel and a selector (String).
     */
    $.osf.applyBindings = function(viewModel, selector) {
        var $elem = $(selector);
        if ($elem.length === 0) {
            throw "No elements matching selector '" + selector + "'";  // jshint ignore: line
        }
        if ($elem.length > 1) {
            throw "Can't bind ViewModel to multiple elements."; // jshint ignore: line
        }
        // Ensure that the bound element is shown
        if ($elem.hasClass('scripted')){
            $elem.show();
        }
        ko.applyBindings(viewModel, $elem[0]);
    };

    $.osf.handleJSONError = function (response) {
        bootbox.alert({
            title: response.responseJSON.message_short,
            message: response.responseJSON.message_long
        });
    };


    /**
     * A date object with two formats: local time or UTC time.
     * @param {String} date The original date as a string. Should be an standard
     *                      format such as RFC or ISO.
     */
    var LOCAL_DATEFORMAT = 'YYYY-MM-DD hh:mm A';
    var UTC_DATEFORMAT = 'YYYY-MM-DD HH:mm UTC';
    $.osf.FormattableDate = function(date) {
        if (typeof date === 'string') {
            // The date as a Date object
            this.date = new Date(date);
        } else {
            this.date = date;
        }
        this.local = moment(date).format(LOCAL_DATEFORMAT);
        this.utc = moment.utc(date).format(UTC_DATEFORMAT);
    };

    // Backwards compatibility
    window.FormattableDate = $.osf.FormattableDate;

    $.widget('custom.catcomplete', $.ui.autocomplete, {
        _renderMenu: function( ul, items ) {
            var that = this;
            var currentCategory = '';
            $.each( items, function( index, item ) {
                if (item.category !== currentCategory ) {
                    ul.append('<li class="ui-autocomplete-category">' + item.category + '</li>' );
                    currentCategory = item.category;
                }
            that._renderItemData( ul, item );
            });
        }
    });


    // TODO: move me to appropriate page-specific module
    $(document).ready(function(){


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

        // Build tooltips on user activity widgets
        $('.ua-meter').tooltip();
        $('[rel=tooltip]').tooltip({
            placement:'bottom'
        });
    });

}));

this.OSFAccountClaimer = (function($, global, undefined) {

    var defaults = {

    };

    /** Validates that the input is an email address.
    * https://stackoverflow.com/questions/46155/validate-email-address-in-javascript
    */
    function validateEmail(email) {
        var re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
        return re.test(email);
    }

    function AccountClaimer (selector, options) {
        this.selector = selector;
        this.element = $(selector);
        this.options = $.extend({}, defaults, options);
        this.init();
    }

    function getClaimUrl() {
        var uid = $(this).data('pk');
        // FIXME: Hack; don't get project id from global
        var pid = global.nodeId;
        return  '/api/v1/user/' + uid + '/' + pid +  '/claim/verify/';
    }

    AccountClaimer.prototype = {
        constructor: AccountClaimer,
        init: function() {
            this.element.editable({
                type: 'text',
                ajaxOptions: {
                    type: 'post',
                    contentType: 'application/json',
                    dataType: 'json'  // Expect JSON response
                },
                success: function(response) {
                    // NOTE: workaround for X-editable to make value not change
                    return {newValue: response.fullname};
                },
                // Send JSON payload
                params: function(params) {
                    return JSON.stringify(params);
                },
                title: 'Claim Account',
                placement: 'bottom',
                value: '',
                placeholder: 'Enter email...',
                validate: function(value) {
                    var trimmed = $.trim(value);
                    if (!validateEmail(trimmed)) {
                        return 'Not a valid email.';
                    }
                },
                url: getClaimUrl.call(this),
                setValue: function(){}
            });
        }
    };

    return AccountClaimer;

})(jQuery, window);

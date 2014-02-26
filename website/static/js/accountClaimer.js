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

    AccountClaimer.prototype = {
        constructor: AccountClaimer,
        init: function() {
            this.element.editable({
                type: 'text',
                title: 'Claim Account',
                placement: 'bottom',
                value: '',
                placeholder: 'Enter email...',
                validate: function(value) {
                    var trimmed = $.trim(value);
                    if (!validateEmail(trimmed)) {
                        return 'Not a valid email.';
                    }
                }
            });
        }
    };

    return AccountClaimer;

})(jQuery, window);

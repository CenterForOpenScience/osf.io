// TODO: Deprecate me
var $ = require('jquery');
var $osf = require('./osfHelpers');

var AddonHelper = (function() {

    /**
     * Convert an HTML form to a JS object.
     *
     * @param {jQuery} form
     * @return {Object} The parsed data
     */
    function formToObj(form) {
        var rv = {};
        $.each($(form).serializeArray(), function(_, value) {
            rv[value.name] = value.value;
        });
        return rv;
    }

    /**
     * Submit add-on settings.
     */
    function onSubmitSettings(options) {
        var $this = $(this);
        var successUpdateMsg = options.successUpdateMsg || 'Setting updated';
        var failUpdateMsg = options.failUpdateMsg || 'Setting not updated';

        var addon = $this.attr('data-addon');
        var owner = $this.find('span[data-owner]').attr('data-owner');
        var msgElm = $this.find('.addon-settings-message');

        var url = owner === 'user' ? '/api/v1/settings/' + addon + '/' : nodeApiUrl + addon + '/settings/';

        $osf.postJSON(
            url,
            formToObj($this)
        ).done(function() {
            msgElm.text(successUpdateMsg)
                .removeClass('text-danger').addClass('text-success')
                .fadeOut(100).fadeIn();
        }).fail(function(response) {
            var message = '';
            response = JSON.parse(response.responseText);
            if (response && response.message) {
                message = response.message;
            } else {
                message = failUpdateMsg;
            }
            msgElm.text(message)
                .removeClass('text-success').addClass('text-danger')
                .fadeOut(100).fadeIn();
        });

        return false;

    }

    // Expose public methods
    exports = {
        formToObj: formToObj,
        onSubmitSettings: onSubmitSettings,
    };

    if (typeof module === 'object') {
        module.exports = exports; 
    } 
    return exports;
})();

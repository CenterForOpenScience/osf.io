var AddonHelper = require('addon-helpers');
var $ = require('jquery');
require('./s3-node-settings.js');

if (!window.contextVars.currentUser.hasAuth) {

    $(document).ready(function () {

        $(window.contextVars.s3SettingsSelector).on('submit', function (evt) {
            evt.preventDefault();
            var $this = $(this);
            var addon = $this.attr('data-addon');
            var msgElm = $this.find('.addon-settings-message');
            var url = window.contextVars.node.urls.api + addon + '/authorize/';

            $.ajax({
                url: url,
                data: JSON.stringify(AddonHelper.formToObj($this)),
                type: 'POST',
                contentType: 'application/json',
                dataType: 'json'
            }).done(function () {
                msgElm.text('S3 access keys loading...')
                        .removeClass('text-danger').addClass('text-info')
                        .fadeIn(1000);
                setTimeout(function(){
                    window.location.reload();
                }, 5000);
            }).fail(function (xhr) {
                var message = 'Error: ';
                var response = JSON.parse(xhr.responseText);
                if (response && response.message) {
                    message += response.message;
                } else {
                    message += 'Settings not updated.';
                }
                msgElm.text(message)
                    .removeClass('text-success').addClass('text-danger')
                    .fadeOut(100).fadeIn();
            });

            return false;

        });

    });

} else {
    $(document).ready(function () {
        $(window.contextVars.s3SettingsSelector).on('submit', AddonHelper.onSubmitSettings);
    });
}

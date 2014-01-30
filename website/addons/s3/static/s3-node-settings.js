var force = '';
function onSubmitRemove() {
    var $this = $(this),
    addon = $this.attr('data-addon'),
    msgElm = $this.find('.addon-settings-message');
    $.ajax({
        url: nodeApiUrl + '${addon_short_name}' + '/settings/delete/' + force,
        type: 'POST',
        contentType: 'application/json',
        dataType: 'json',
    }).success(function() {
        msgElm.text('Access removed')
            .removeClass('text-danger').addClass('text-success')
            .fadeOut(100).fadeIn();
    }).fail(function(xhr) {
        var message = 'Error: Access not removed';
        msgElm.text(message)
            .removeClass('text-success').addClass('text-danger')
            .fadeOut(100).fadeIn();
        btn = $this.find('.addon-settings-submit');
        btn.text('Force Removal');
        btn.attr('class', 'btn btn-warning addon-settings-submit')
        force = 'force/';
    });
    return false;
});

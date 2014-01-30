var force = '';
function onSubmitRemove() {
    var $this = $(this),
    addon = $this.attr('data-addon'),
    msgElm = $this.find('.addon-settings-message');
    $.ajax({
        url: nodeApiUrl +  addonShortname + '/settings/delete/' + force,
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
};


//TODO Fix me up set bucketname variable.
function setDropDownListener() {
    $( document.body ).on( 'click', '.dropdown-menu li', function( event ) {

       var $target = $( event.currentTarget );

       $target.closest( '.btn-group' )
          .find( '[data-bind="label"]' ).text( $target.text() )
             .end()
          .children( '.dropdown-toggle' ).dropdown( 'toggle' );
          $('#s3_bucket').attr('value', $target.text());
        //Submit Form here
        $('#addonSettingsS3').submit();
        //AddonHelper.onSubmitSettings();
        return false;


    });
};

function newBucket(bucketName) {

};

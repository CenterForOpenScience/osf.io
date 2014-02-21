//TODO Fix me up use id's maybe...
function setDropDownListener() {
    $( document.body ).on( 'click', '.dropdown-menu li', function( event ) {

       var $target = $( event.currentTarget );

       $target.closest( '.btn-group' )
          .find( '[data-bind="label"]' ).text( $target.text() )
             .end()
          .children( '.dropdown-toggle' ).dropdown( 'toggle' );
          $('#s3_bucket').attr('value', $target.text());
        //Submit Form here
        if ($target.text().indexOf('Create a new bucket') != -1) {
            newBucket();
        } else if ($target.text().indexOf('Deauthorize') != -1) {
            removeNodeAuth();
            return false;
        } else {
            $('#addonSettingsS3').submit();
        }

        return false;

    });
}

function newBucket() {
    bootbox.prompt('Name your new bucket', function(bucketName) {
      if (!bucketName)
        return;
        bucketName = bucketName.toLowerCase();
        $.ajax({
            url: nodeApiUrl +  addonShortname + '/newbucket/',
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            data: JSON.stringify({bucket_name: bucketName})
        }).done(function() {
            $('#bucketlabel').text(bucketName);
            $('#s3_bucket').val(bucketName);
            $('#s3-dropdown').find('li').first().after('<li role="presentation"><a href="#">' + bucketName + '</a></li>')
            $('#addonSettingsS3').submit();
        }).fail(function(xhr) {
            bootbox.confirm('Looks like that name is taken. Try another name?', function(result) {
                if (result)
                    newBucket();
            })
        });

    });
};

function removeNodeAuth()
{
    $.ajax({
        url: nodeApiUrl + addonShortname + '/settings/',
        type: 'DELETE',
        contentType: 'application/json',
        dataType: 'json'
    }).done(function() {
        location.reload();
    }).fail(function(xhr) {
        //TODO Do something here
    });
}

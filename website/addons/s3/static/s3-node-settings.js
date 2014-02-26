(function() {

    function newBucket() {

        var $elm = $('#addonSettingsS3');
        var $select = $elm.find('select');

        bootbox.prompt('Name your new bucket', function(bucketName) {

            if (!bucketName) {
              return;
            }
            bucketName = bucketName.toLowerCase();
            $.ajax({
                type: 'POST',
                url: nodeApiUrl +  's3/newbucket/',
                contentType: 'application/json',
                dataType: 'json',
                data: JSON.stringify({bucket_name: bucketName})
            }).done(function() {
                $select.append('<option value="' + bucketName + '">' + bucketName + '</option>');
                $select.val(bucketName);
            }).fail(function(xhr) {
                bootbox.confirm('Looks like that name is taken. Try another name?', function(result) {
                    if (result) {
                        newBucket();
                    }
                })
            });

        });

    }

    var removeNodeAuth = function() {
        $.ajax({
            type: 'DELETE',
            url: nodeApiUrl + 's3/settings/',
            contentType: 'application/json',
            dataType: 'json',
            success: function(response) {
                window.location.reload();
            },
            error: function(xhr) {
                //TODO Do something here
            }
        });
    };

    $(document).ready(function() {

        $('#newBucket').on('click', function() {
            newBucket();
        });

        $('#s3RemoveToken').on('click', function() {
            bootbox.confirm(
                'Are you sure you want to remove this S3 authorization?', function(confirm) {
                    if (confirm) {
                        removeNodeAuth();
                    }
                }
            );
        });

        $('#addonSettingsS3 .addon-settings-submit').on('click', function() {
            var $bucket = $('#s3_bucket');
            if ($bucket.length && !$bucket.val()) {
                return false;
            }
        });

    });

})();

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

    $(document).ready(function() {
        $('#newBucket').on('click', function() {
            newBucket();
        });
    });

})();
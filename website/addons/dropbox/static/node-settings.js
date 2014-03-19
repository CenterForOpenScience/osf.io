var DropboxConfigHelper = (function() {

    var bloodhound;

    $(document).ready(function() {

        var options = [
            {text:'Root', value:'/'},
            {text:'TestFolder', value:'/TestFolder/'}
        ];

        bloodhound = new Bloodhound({
            datumTokenizer: Bloodhound.tokenizers.obj.nonword('text'),
            queryTokenizer: Bloodhound.tokenizers.nonword,
            local: options
        });

        bloodhound.initialize();

        $('#dropboxFolderSelect').typeahead({
          highlight: true,
          minLength: 0,
          hint: false
        },
        {
            name: 'projects',
            displayKey: 'text',
            source: wrapHound
        });

        $('#dropboxFolderSelect').on('change paste keyup', enable);
        $('#dropboxFolderSelect').on('focus', dropDown);
        $('#dropboxFolderSelect').on('typeahead:autocompleted typeahead:selected', makeSubmit);
    });

    var enable = function() {
        if($(this).val() && $(this).val().trim())
            $('#dropboxSubmit').prop('disabled', false);
        else {
            $('#dropboxSubmit').prop('disabled', true);
            $('#dropboxSubmit').text('Create');
            $('#dropboxSubmit').removeClass('btn-success');
            $('#dropboxSubmit').addClass('btn-primary');
        }
    }

    var makeSubmit = function(){
        $('#dropboxSubmit').text('Submit');
        $('#dropboxSubmit').removeClass('btn-primary');
        $('#dropboxSubmit').addClass('btn-success');
    }

    var wrapHound = function(query, cb) {
        if (query != '')
            bloodhound.get(query, cb);
        else
            cb(bloodhound.local);
    }

    var dropDown = function() {
        //Todo This
        $(this).update('');
    }

})();

//TODO Template ify
//Dropdown all

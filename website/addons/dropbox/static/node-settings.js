    stuff = [
        {text:'Root', value:'/'},
        {text:'TestFolder', value:'/TestFolder/'}
    ];

    var bloodhound = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.obj.nonword('text'),
        queryTokenizer: Bloodhound.tokenizers.nonword,
        local: stuff
    });

    bloodhound.initialize();



    $('#figshareSelect').typeahead({
      highlight: true,
      minLength: 0
    },
    {
        name: 'projects',
        displayKey: 'text',
        source: bloodhound.ttAdapter()
    });
    $('#figshareSelect').on('change paste keyup',function() {
        if($(this).val() && $(this).val().trim())
            $('#figshareSubmit').prop('disabled', false);
        else
            $('#figshareSubmit').prop('disabled', true);
    });

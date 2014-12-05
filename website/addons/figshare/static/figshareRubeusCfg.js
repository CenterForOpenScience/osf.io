;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['js/rubeus'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('rubeus', function() { factory(Rubeus); });
    } else { factory(Rubeus); }
}(this, function(Rubeus) {

    Rubeus.cfg.figshare = {
        // Custom error message for when folder contents cannot be fetched
        FETCH_ERROR: '<span class="text-danger">This Figshare folder may ' +
                        'have been renamed or deleted. ' +
                        'Please select a folder at the settings page.</span>'
    };

}));


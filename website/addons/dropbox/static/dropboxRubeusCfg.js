
var Rubeus = require('rubeus');

Rubeus.cfg.dropbox = {
    // Custom error message for when folder contents cannot be fetched
    FETCH_ERROR: '<span class="text-danger">This Dropbox folder may ' +
                    'have been renamed or deleted. ' +
                    'Please select a folder at the settings page.</span>'
};

var Fangorn = require('fangorn');


Fangorn.config.osfstorage = {
    /**
     * Tornado probabilistically interrupts the connection with the client
     * when an error is raised in `prepare` or `data_received`. Detect the
     * disconnect event and a 409 and raise a more helpful error message.
     * See https://groups.google.com/forum/#!topic/python-tornado/-8GUVdSPp2k
     * for details.
     */
    uploadError: function(file, message) {
        if (message === 'Server responded with 0 code.' || message.indexOf('409') !== -1) {
            return 'Unable to upload file. Another upload with the ' +
                'same name may be pending; please try again in a moment.';
        }
    }

};

'use strict';

var pym = require('pym.js');

var registrationURL = window.contextVars.share.urls.registrationURL;

new pym.Parent(
    'share_registration_iframe',
    registrationURL,
    {}
);

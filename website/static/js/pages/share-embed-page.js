'use strict';

var pym = require('pym.js');

var registration_url = window.contextVars.share.registration_url;

var pymParent = new pym.Parent(
    'share_registration_iframe',
    registration_url,
    {}
);

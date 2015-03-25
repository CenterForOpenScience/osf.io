'use strict';

var pym = require('pym.js');

var register = window.contextVars.share.urls.register;

new pym.Parent(
    'share_registration_iframe',
    register,
    {}
);

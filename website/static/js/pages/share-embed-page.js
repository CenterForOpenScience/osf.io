'use strict';

var pym = require('pym.js');

var register = window.contextVars.share.urls.register;

var pymParent = new pym.Parent(
    'share_registration_iframe',
    register,
    {}
);

function scrollToTop(data) {
    window.scrollTo(0, 0);
}

pymParent.onMessage('scroll_top_now', scrollToTop)

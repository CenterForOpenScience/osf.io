var $ = require('jquery');
var m = require('mithril');
var LogWrap = require('js/recentActivityWidget');
require('css/home.css');

$(document).ready(function() {
    m.mount(document.getElementById('recentActivityWidget'), m.component(LogWrap, {userId: window.contextVars.userId}));
});

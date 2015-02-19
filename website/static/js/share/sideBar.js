var m = require('mithril');

var SideBar = {};

SideBar.view = function(ctrl) {
    return m('.row', [
        m('img[src=/static/img/share-logo.png]', {
            style: { 'max-width': '50%', height: 'auto' }
        })
    ]);
};

SideBar.controller = function() {
};

module.exports = SideBar;

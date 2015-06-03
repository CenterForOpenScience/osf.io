var $ = require('jquery');
var m = require('mithril');


function Panel(title, header, inner, args, selected) {
    panel = m.component(Panel, title, header, inner, args);
    panel.title = title;
    panel.selected = selected || false;
    return panel;
}


Panel.controller = function(title, header, inner, args) {
    var self = this;
    self.title = title;
    self.header = header === null ? null : header || title;
    self.inner = m.component.apply(self, [inner].concat(args || []));
};


Panel.view = function(ctrl) {
    return m('#' + ctrl.title.toLowerCase() + 'Panel', [
        !ctrl.header ? '' :
            m('.osf-panel-header', $.isFunction(ctrl.header) ? ctrl.header() : ctrl.header),
        m('', ctrl.inner)
    ]);
};


var Spinner = m.component({
    controller: function(){},
    view: function() {
        return m('.fangorn-loading', [
            m('.logo-spin.text-center', [
                m('img[src=/static/img/logo_spin.png][alt=loader]')
            ]),
            m('p.m-t-sm.fg-load-message', ' Loading... ')
        ]);
    }
});


module.exports = {
    Panel: Panel,
    Spinner: Spinner,
};

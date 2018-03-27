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
    return m('#' + ctrl.title.toLowerCase() + 'Panel.panel.panel-default', [
        !ctrl.header ? '' :
            m('.panel-heading', $.isFunction(ctrl.header) ? ctrl.header() : ctrl.header),
        m('', ctrl.inner)
    ]);
};


var Spinner = m.component({
    controller: function(){},
    view: function() {
        return m('.spinner-loading-wrapper', [
            m('.ball-scale.ball-scale-blue', [m('div')]),
            m('p.m-t-sm.fg-load-message', ' Loading... ')
        ]);
    }
});


module.exports = {
    Panel: Panel,
    Spinner: Spinner,
};

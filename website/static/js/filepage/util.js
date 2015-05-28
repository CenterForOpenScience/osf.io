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
    self.header = header || title;
    self.inner = m.component.apply(self, [inner].concat(args || []));
};


Panel.view = function(ctrl) {
    return m('.osf-panel', [
        m('.osf-panel-header', ctrl.header),
        m('.osf-panel-body', ctrl.inner)
    ]);
};


var PanelToggler = {
    controller: function(header, panels) {
        var self = this;
        self.panels = panels;
        self.header = header || '';
    },
    view: function(ctrl) {
        var shown = ctrl.panels.reduce(function(accu, panel) {
            return accu + (panel.selected ? 1 : 0);
        }, 0);

        return m('.panel-toggler', [
            m('.row', [
                m('.pull-right', [
                    m('.btn-group.btn-group-sm', {class: 'file-toggle-btn'}, [m('.btn.btn-default.disabled', 'Toggle View: ')].concat(
                        ctrl.panels.map(function(panel) {
                            return m('.btn' + (panel.selected ? '.btn-primary' : '.btn-default'), {
                                onclick: function(e) {
                                    e.preventDefault();
                                    panel.selected = !panel.selected;
                                }
                            }, panel.title);
                        })
                    ))
                ])
            ]),
            m('br'),
            m('.row', ctrl.panels.map(function(panel, index) {
                if (!panel.selected) return m('[style="display:none"]', panel);
                return m('.col-md-' + Math.floor(12/shown), panel);
            }))
        ]);
    }
};


var Spinner = m.component({
    controller: function(){},
    view: function() {
        return m('i.fa.fa-spinner.fa-pulse');
    }
});


module.exports = {
    Panel: Panel,
    Spinner: Spinner,
    PanelToggler: PanelToggler
};

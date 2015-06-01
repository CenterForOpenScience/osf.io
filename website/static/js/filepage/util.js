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

        //Dirty hack because of the treebeard redraw issues
        //Dont ever do this
        if (shown === 2) {
            $('#mfrIframeParent').removeClass().addClass('col-md-6');
            $('.file-view-panels').removeClass().addClass('file-view-panels').addClass('col-md-6');
        } else if (shown === 1) {
            $('#mfrIframeParent').removeClass().addClass('col-md-9');
            $('.file-view-panels').removeClass().addClass('file-view-panels').addClass('col-md-3');
        } else {
            $('#mfrIframeParent').removeClass().addClass('col-md-11');
            $('.file-view-panels').removeClass().addClass('file-view-panels').addClass('col-md-1');
        }

        return m('.panel-toggler', [
            m('.row', m('.col-md-12', [
                m('.btn-toolbar.pull-right[style="width:355px!important;"]', [
                    m('.btn-group.btn-group-sm.file-toggle-btn.pull-right', [
                        m('.btn.btn-default.disabled', 'Toggle View: ')
                    ].concat(
                        ctrl.panels.map(function(panel) {
                            return m('.btn' + (panel.selected ? '.btn-primary' : '.btn-default'), {
                                onclick: function(e) {
                                    e.preventDefault();
                                    panel.selected = !panel.selected;
                                }
                            }, panel.title);
                        })
                    )),
                    m('.btn.btn-sm.btn-danger.pull-right', {onclick: $(document).trigger.bind($(document), 'fileviewpage:delete')}, 'Delete'),
                    m('.btn.btn-sm.btn-success.pull-right', {onclick: $(document).trigger.bind($(document), 'fileviewpage:download')}, 'Download'),
                ])
            ])),
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
    PanelToggler: PanelToggler
};

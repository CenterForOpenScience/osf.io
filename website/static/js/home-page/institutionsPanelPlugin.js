/**
 * Display a horizontal listing of clickable OSF4I logos (links to institution landing pages).
 */
'use strict';

var $ = require('jquery');
var m = require('mithril');
var utils = require('js/components/utils');
var required = utils.required;

var components = require('js/components/institution');
var Institution = components.InstitutionImg;

var LOGO_WIDTH = '120px';

var InstitutionsPanel = {
    controller: function() {
        // Helper method to render logo link
        this.renderLogo = function(inst, opts) {
            var href = '/institutions/' + inst.id + '/';
            return m('a', {href: href},
                        [m.component(Institution,
                                    {
                                        name: inst.name,
                                        logoPath: inst.logoPath,
                                        muted: opts.muted,
                                        width: LOGO_WIDTH,
                                        style: {'margin-right': '15px'}
                                    })]);
        };
    },
    view: function(ctrl, opts) {
        var affiliated = required(opts, 'affiliatedInstitutions');
        var allInstitutions = required(opts, 'allInstitutions');

        var affiliatedIds = affiliated.map(function(inst) { return inst.id; });
        var unaffiliated = allInstitutions.filter(function(inst) {
            return $.inArray(inst.id, affiliatedIds) === -1;
        });

        return m('.p-v-sm',
            m('.row',
                [
                    m('.col-md-12',
                        // Display affiliated institutions before unaffiliated institutions
                        affiliated.map(function(inst) { return ctrl.renderLogo(inst, {muted: false}); })
                            .concat(unaffiliated.map(function(inst) { return ctrl.renderLogo(inst, {muted: true}); }))
                    )
                ]
            )
        );
    }
};

module.exports = InstitutionsPanel;

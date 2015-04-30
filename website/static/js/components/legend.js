require('css/legend.css');

var m = require('mithril');

module.exports = function(data, opts) {
    var title = opts.title || 'Legend';
    return [m('h3', title), 
            m('hr'),
            m('div', {
            className: 'legend-grid'
            }, data.map(function(item) {
                return m('span', {
                    className: 'legend-grid-item'
                }, [
                    m('span', {
                        className: item.icon
                    }), 
                    '  ',
                    item.label
                ]);
            })),
            m('hr'),
            m('span', {
                className: 'legend-footer'
            }, opts.footer || '')
           ];
};

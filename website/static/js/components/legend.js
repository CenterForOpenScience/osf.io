require('css/legend.css');
var m = require('mithril');

module.exports = {
    view: function(data, repr, opts) {
        if(data[0].label){
            data.sort(function(a, b) {
                return a.label.localeCompare(b.label);
            });
        }
        return [
            m('div', {
                className: 'legend-grid'
            }, data.map(function(item) {
                return m('span', {
                    className: 'legend-grid-item'
                }, repr(item));
            })),
            m('span', {className: 'pull-left'}, opts.footer || '')
        ];
    }
};

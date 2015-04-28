require('css/legend.css');

var m = require('mithril');

var chunk = function(list, step) {
    var ret = [];
    var piece = [];
    for (var i = 0; i < list.length; i++) {
        piece.push(list[i]);
        if (piece.length === step) {
            ret.push(piece);
            piece = [];
        }
    }
    if (piece.length) {
        ret.push(piece);
    }
    return ret;
};

module.exports = function(data, opts) {
    var width = opts.width || 3;
    var title = opts.title || 'Legend';
    return [m('h3', title), 
            m('hr'),
            m('table', {
            className: 'legend-table table'
            }, [
                chunk(data, width).map(function(set) {
                    return m('tr', set.map(function(item) {
                        return m('td', [
                            m('span', {
                                className: item.icon
                            }), 
                            '  ',
                            item.label
                        ]);
                    }));
                })
            ]),
            opts.extra
           ];
};

require('css/legend.css');
var m = require('mithril');

module.exports = {
    view: function (data, repr, opts) {
        if (data[0].label) {
            /* sorting should be:
               [ (IN alpha order), Other, Uncategorized]

                sort a b
                    a == Uncat     =  1
                    b == Uncat     = -1
                    a == Other
                        b == Uncat = -1
                        otherswise =  1
                    b == Other
                        a == Uncat =  1
                        otherwise  = -1
                    otherwise      = compare a b
             */
            data.sort(function (a, b) {
                // Uncategorized should come last
                if(a.label === 'Uncategorized') return  1;
                if(b.label === 'Uncategorized') return -1;

                // Other should come second to last
                if(a.label === 'Other') {
                    if(b.label === 'Uncategorized') {
                        return -1;
                    }
                    return 1;
                }

                if(b.label === 'Other') {
                    if(a.label === 'Uncategorized') {
                        return 1;
                    }
                    return -1;
                }

                // Otherwise order regularly
                return a.label.localeCompare(b.label);
            });
        }
        return [
            m('div', {
                className: 'legend-grid'
            }, data.map(function (item) {
                return m('span', {
                    className: 'legend-grid-item'
                }, repr(item));
            })),
            m('span', {className: 'pull-left'}, opts.footer || '')
        ];
    }
};

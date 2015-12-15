require('css/legend.css');
var m = require('mithril');

/** Finds the index of a string in an array
 *
 * @param {Array} array The array to search through
 * @param {String} str The string to find
 * @returns {*}
 */
var find_index = function (array, str) {
    for (var i = 0; i < array.length; i++) {
        console.log(array[i].label);
        if (array[i].label === str)
            return i;
    }
    return -1;
};

/** Removes an index from an array immutably
 *
 * @param {Array} array the array to modify
 * @param {Int} index the index to remove
 * @returns {*} a new array missing the index value
 */
var remove_index = function (array, index) {
    var new_array = [];
    for (var i = 0; i < array.length; i++) {
        if (i !== index)
            new_array.push(array[i]);
    }
    return new_array;
};

module.exports = {
    view: function (data, repr, opts) {
        var other_index = find_index(data, 'Other');
        var other = data[other_index];
        data = remove_index(data, other_index);

        var uncat_index = find_index(data, 'Uncategorized');
        var uncat = data[uncat_index];
        data = remove_index(data, uncat_index);

        if (data[0].label) {
            data.sort(function (a, b) {
                return a.label.localeCompare(b.label);
            });
        }

        data.push(other);
        data.push(uncat);

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

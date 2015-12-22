'use strict';

var $ = require('jquery');

var responsiveTable = function(table) {
    var headers = table.querySelectorAll('th');
    var rows = table.querySelectorAll('tbody>tr');
    for (var j = 0, row; row = rows[j]; j++) {
        responsiveRow(row, headers);
    }
};

var responsiveRow = function(row, headers) {
    if (headers === undefined) {
        headers = row.parentElement.parentElement.querySelectorAll('th');
    }
    for (var k = 0, cell; cell = row.cells[k]; k++) {
        var $cell = $(cell);
        if ($cell.has('*').length === 0) {
            cell.innerHTML = '<p>' + cell.innerHTML + '</p>';
        }
        if ($cell.has('div.header').length === 0  && !$(headers[k]).hasClass('responsive-table-hide') && headers[k].innerHTML !== '') {
            $cell.prepend('<div class=\'header\'>' + headers[k].innerHTML.replace(/\r?\n|\r/, '') + '</div>');
        }
        else if ($cell.has('div.header').length === 1) {
            $cell.children().filter('div.header').html(headers[k].innerHTML.replace(/\r?\n|\r/, ''));
        }
    }
};

module.exports = {
    responsiveTable: responsiveTable,
    responsiveRow: responsiveRow
};

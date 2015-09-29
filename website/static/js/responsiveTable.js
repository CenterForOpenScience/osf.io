var responsiveTable = function(table) {
    var headers = table.querySelectorAll('th');
    var rows = table.querySelectorAll('tbody>tr');
    for (var j = 0, row; row = rows[j]; j++) {
        for (var k = 0, cell; cell = row.cells[k]; k++) {
            if (jQuery(cell).hasClass('to-top')) {
                jQuery(cell.firstElementChild).clone(true).appendTo(row.firstElementChild);
            }
            else {
                if (jQuery(cell).has("*").length == 0) {
                    cell.innerHTML = "<p>" + cell.innerHTML + "</p>";
                }
                if (jQuery(cell).has("div.header").length == 0) {
                    jQuery(cell).prepend("<div class='header'>" + headers[k].innerHTML.replace(/\r?\n|\r/, "") + "</div>");
                }
            }
        }
    }
};

module.exports = responsiveTable;

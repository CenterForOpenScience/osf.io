var $ = require('jquery');
require('bootstrap-datepicker');
require('bootstrap-datepicker-ja');
require('bootstrap-datepicker-css');

function mount(selector, datepicker_locale) {
    var show_func = function(e) {
        $('.datepicker-dropdown').css('background-color', '#FFF');
    };
    var opt = {
        format: 'yyyy-mm-dd',
        language: datepicker_locale,
        zIndexOffset: 1050,
        todayBtn: true,
        todayHighlight: true
    };
    $(selector).datepicker(opt).on('show', show_func);
}

module.exports = {
    mount: mount
};

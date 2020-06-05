var $ = require('jquery');
require('bootstrap-datepicker');
require('bootstrap-datepicker-ja');
require('bootstrap-datepicker-css');

var gt = require('js/rdmGettext');

function mount(selector, datepicker_locale) {
    if (datepicker_locale === null || datepicker_locale.length === 0) {
        datepicker_locale = gt.getBrowserLang();
    }
    var show_func = function(e) {
        $('.datepicker-dropdown').css('background-color', '#FFF');
    };
    var opt = {
        format: 'yyyy-mm-dd',
        language: datepicker_locale,
        zIndexOffset: 1050,
        clearBtn: false,
        todayBtn: true,
        todayHighlight: true
    };
    return $(selector).datepicker(opt).on('show', show_func);
}

module.exports = {
    mount: mount
};

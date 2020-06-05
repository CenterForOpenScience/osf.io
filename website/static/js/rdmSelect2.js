var $ = require('jquery');
var gt = require('js/rdmGettext');
require('select2');

var locale = gt.getBrowserLang();
if (locale === 'ja') {
    require('select2-ja');
}

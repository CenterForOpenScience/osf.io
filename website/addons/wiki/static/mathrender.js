'use strict';

var $ = require('jquery');
var MathJax = require('MathJax');

/**
 * Render math with MathJax within a given element.
 * */
function mathjaxify(previewSelector) {
    var $elem = $(previewSelector);
    function typesetStubbornMath() {
        $elem.each(function() {
            if ($(this).text() !== '') {
                MathJax.Hub.Queue(['Typeset', MathJax.Hub, $(this).attr('id')]);
            }
        });
    }
    var preview = $elem[0];
    if (typeof(typeset) === 'undefined' || typeset === true) {
        MathJax.Hub.Queue(['Typeset', MathJax.Hub, preview]);
        typesetStubbornMath();
    }
}


module.exports = {
    mathjaxify: mathjaxify
};

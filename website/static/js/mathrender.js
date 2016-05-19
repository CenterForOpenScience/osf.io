'use strict';

var $ = require('jquery');
var MathJax = require('MathJax');

/**
 * Render math with MathJax within a given element.
 * */
function mathjaxify(selector) {
    var $elem = $(selector);
    function typesetStubbornMath() {
        $elem.each(function() {
            if ($(this).text() !== '') {
                MathJax.Hub.Queue(['Typeset', MathJax.Hub, $(this).attr('id')]);
            }
        });
    }
    var preview = $elem[0];
    if (typeof(window.typeset) === 'undefined' || window.typeset === true) {
        MathJax.Hub.Queue(['Typeset', MathJax.Hub, preview]);
        typesetStubbornMath();
    }
}

// Helper function takes an element node and typesets its math markup.
function typeset(el) {
    function randomStringGen(length) {
        if (typeof length !== "number") length = 8;
        var text = "";
        var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
        for(var i = 0; i < length; i++) {
            text += possible.charAt(Math.floor(Math.random() * possible.length));
        }
        return text;
    };
    
    MathJax.Hub.Config({
        tex2jax: {inlineMath: [['$','$'], ['\\(','\\)']]}
    });
    
    // If our element is not an element node, it can't have an id,
    // and so MathJax cannot process it. Let's print 
    // something helpful to the console and return from the funciton early.                  
    if (el.nodeType != 1) {   
        console.log("Trying to typeset non-node "+el.id+", or node does not exist in DOM.\n"
                   +"Check the element's id is correct and that it exists.");
        return false;
    };
    
    // MathJax requires an id to target elements.
    // We create a random string to serve as an id.
    // 32 chars should be enouth entrop to prevent
    // collisions.
    el.id = randomStringGen(32); 
    
    // Add an element by its id to MAthJax Queue to typeset.
    // As soon as MathJax has a queue, it'll start typesetting.
    window.MathJax.Hub.Queue(["Typeset", MathJax.Hub, el.id]);
}


module.exports = {
    mathjaxify: mathjaxify,
    typeset: typeset
};

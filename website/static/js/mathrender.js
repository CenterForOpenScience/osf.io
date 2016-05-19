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
        MathJax.Hub.Queue(['Typeset', MathJax.Hub, preview]); // This function takes an id, not a node... what are we doing here?
        typesetStubbornMath(); // If the line above does work, we're doing the same thing again (and more, granted) here.
    }
}

// Generate a random string suitable for use as an id.
function randomStringGen(length) {
    if (typeof length !== "number") length = 8;
    var text = "";
    var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    for(var i = 0; i < length; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
};    

// Helper function takes an element node and typesets its math markup.
// This can now be mapped over a nodelist or the like.
function typeset(el) {

    console.log("Typesetting elements...");  
 
    // If our element is not an element node, it can't have an id,
    // and so MathJax cannot process it. Let's print 
    // something helpful to the console and return from the funciton early.                  
    if (el.nodeType !== 1) {   
        console.log("Trying to typeset non-node "+el.id+", or node does not exist in DOM.\n"
                   +"Check the element's id is correct and that it exists.");
        return false;
    };
    
    // MathJax requires an id to target elements.
    // We create a random string to serve as an id.
    // while checking for a collision if the target
    // node does not have an id.
    if ( typeof el.id === "undefined" || el.id.length === 0 ) {
        do { var id = randomStringGen(16); } while (document.getElementById(id));
        el.id = id; 
    }
    
    // Make sure we're doing this in a browser...
    // This isn't _really_ a good enough guard against this getting 
    // run on the server, but hopefully we don't define window...
    if (typeof window === "undefined") return;
        
    // Configure ajax // TODO: Put this in a config file!
    window.MathJax.Hub.Config({
        tex2jax: {inlineMath: [['$','$'], ['\\(','\\)']]}
    });
    
    // Add an element by its id to MAthJax Queue to typeset.
    // As soon as MathJax has a queue, it'll start typesetting.
    window.MathJax.Hub.Queue(["Typeset", MathJax.Hub, el.id]);

}


module.exports = {
    mathjaxify: mathjaxify,
    typeset: typeset
};

var jsdiff = require('jsdiff');

// Taken from diff.js
function removeEmpty(array) {
    var ret = [];
    for (var i = 0; i < array.length; i++) {
        if (array[i]) {
            ret.push(array[i]);
        }
    }
    return ret;
}

// Custom differ that includes newlines and sentence breaks
var wikiDiff =  new jsdiff.Diff();
wikiDiff.tokenize = function (value) {
    return removeEmpty(value.split(/(\S.+?[.!?\n])(?=\s+|$)/));
};

var diff = function(beforeText, afterText) {
    var diffList = wikiDiff.diff(beforeText, afterText);
    var fragment = document.createDocumentFragment();

    diffList.forEach(function(part) {
        var color = part.added ? 'text-success' : part.removed ? 'text-danger' : '';
        var span = part.removed ? document.createElement('s') : document.createElement('span');
        span.className = color;
        span.appendChild(document.createTextNode(part.value));
        fragment.appendChild(span);
    });

    var output = $('<div>').append(fragment).html();
    return output;
};

module.exports = {
    diff: diff
};
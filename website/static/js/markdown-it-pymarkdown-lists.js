// Lists -- markdown-it to pymarkdown!
// Adapted from markdown-it.js block list rule (MIT Licensed)

'use strict';


function isSpace(code) {
    switch (code) {
        case 0x09:
        case 0x20:
            return true;
    }
    return false;
}

// Search `[-+*][\n ]`, returns next pos arter marker on success
// or -1 on fail.
function skipBulletListMarker(state, startLine) {
    var marker, pos, max;

    pos = state.bMarks[startLine] + state.tShift[startLine];
    max = state.eMarks[startLine];

    marker = state.src.charCodeAt(pos++);
    // Check bullet
    if (marker !== 0x2A/* * */ &&
            marker !== 0x2D/* - */ &&
            marker !== 0x2B/* + */) {
        return -1;
    }

    if (pos < max && !isSpace(state.src.charCodeAt(pos))) {
        // " 1.test " - is not a list item
        return -1;
    }

    return pos;
}

// Search `\d+[.)][\n ]`, returns next pos arter marker on success
// or -1 on fail.
function skipOrderedListMarker(state, startLine) {
    var ch,
            pos = state.bMarks[startLine] + state.tShift[startLine],
            max = state.eMarks[startLine];

    // List marker should have at least 2 chars (digit + dot)
    if (pos + 1 >= max) { return -1; }

    ch = state.src.charCodeAt(pos++);

    if (ch < 0x30/* 0 */ || ch > 0x39/* 9 */) {
        return -1;
    }

    for (;;) {
        // EOL -> fail
        if (pos >= max) { return -1; }

        ch = state.src.charCodeAt(pos++);

        if (ch >= 0x30/* 0 */ && ch <= 0x39/* 9 */) {
            continue;
        }

        // found valid marker
        if (ch === 0x29/* ) */ || ch === 0x2e/* . */) {
            break;
        }

        return -1;
    }


    if (pos < max && !isSpace(state.src.charCodeAt(pos))/* space */) {
        // " 1.test " - is not a list item
        return -1;
    }
    return pos;
}

function markTightParagraphs(state, idx) {
    var i, l, level = state.level + 2;

    for (i = idx + 2, l = state.tokens.length - 2; i < l; i++) {
        if (state.tokens[i].level === level && state.tokens[i].type === 'paragraph_open') {
            state.tokens[i + 2].hidden = true;
            state.tokens[i].hidden = true;
            i += 2;
        }
    }
}

function hideOldListContent(state, idx) {
    var i, l;
    if (idx > 1) {
        for (i = idx - 2, l = state.tokens.length; i < l; i++) {
            state.tokens[i].hidden = true;
            state.tokens[i].content = '';
        }
    }
}


module.exports = function list(state, startLine, endLine, silent) {
    var nextLine,
            content,
            indent,
            oldTShift,
            oldIndent,
            oldTight,
            oldParentType,
            start,
            posAfterMarker,
            max,
            indentAfterMarker,
            markerValue,
            markerCharCode,
            isOrdered,
            contentStart,
            firstStartLine,
            listTokIdx,
            prevEmptyEnd,
            listLines,
            itemLines,
            tight = true,
            terminatorRules,
            token,
            i, l, terminate;

    // Detect list type and position after marker
    if ((posAfterMarker = skipOrderedListMarker(state, startLine)) >= 0) {
        isOrdered = true;
    } else if ((posAfterMarker = skipBulletListMarker(state, startLine)) >= 0) {
        isOrdered = false;
    } else {
        return false;
    }

    // save variable to state to check if the list should be rendered
    if (!state.isEmpty(startLine - 1) && startLine !== 0) {
        state.renderList = false;
    } else {
        state.renderList = true;
    }

    // Save the first start line for putting into one token if list shouldn't be rendered
    firstStartLine = startLine;

    // Remember char code to set it later on
    markerCharCode = state.src.charCodeAt(posAfterMarker - 1);

    // For validation mode we can terminate immediately
    if (silent) {
        return true;
    }

    // Start list - token index of where the list begins
    listTokIdx = state.tokens.length;

    if (isOrdered) {
        start = state.bMarks[startLine] + state.tShift[startLine];
        markerValue = Number(state.src.substr(start, posAfterMarker - start - 1));

        if (state.renderList) {
            token = state.push('ordered_list_open', 'ol', 1);
            token.map = listLines = [ startLine, 0 ];
        } else {
            listLines = [];
        }
        if (markerValue > 1) {
            token.attrs = [['start', markerValue ]];
        }

    } else {
        if (state.renderList) {
            token = state.push('bullet_list_open', 'ul', 1);
            token.markup = String.fromCharCode(markerCharCode);
            token.map = listLines = [ startLine, 0 ];
        } else {
            listLines = [];
        }
    }

    //
    // Iterate list items
    //

    nextLine = startLine;
    prevEmptyEnd = false;
    terminatorRules = state.md.block.ruler.getRules('list');

    while (nextLine < endLine) {
        contentStart = state.skipSpaces(posAfterMarker);
        max = state.eMarks[nextLine];

        if (contentStart >= max) {
            // trimming space in "-    \n  3" case, indent is 1 here
            indentAfterMarker = 1;
        } else {
            indentAfterMarker = contentStart - posAfterMarker;
        }

        // If we have more than 4 spaces, the indent is 1
        // (the rest is just indented code block)
        if (indentAfterMarker > 4) { indentAfterMarker = 1; }

        // "  -  test"
        //  ^^^^^ - calculating total length of this thing
        indent = (posAfterMarker - state.bMarks[nextLine]) + indentAfterMarker;

        // Run subparser & write tokens
        if (state.renderList) {
            token        = state.push('list_item_open', 'li', 1);
            token.markup = String.fromCharCode(markerCharCode);
            token.map    = itemLines = [ startLine, 0 ];
        } else {
            itemLines = [];
        }

        oldIndent = state.blkIndent;
        oldTight = state.tight;
        oldTShift = state.tShift[startLine];
        oldParentType = state.parentType;
        state.tShift[startLine] = contentStart - state.bMarks[startLine];
        state.blkIndent = indent;
        state.tight = true;
        state.parentType = 'list';

        state.md.block.tokenize(state, startLine, endLine, true);

        // If any of list item is tight, mark list as tight
        if (!state.tight || prevEmptyEnd) {
            tight = false;
        }

        // Item becomes loose if it ends with an empty line,
        // should filter last element, because it means the list is finished
        prevEmptyEnd = (state.line - startLine) > 1 && state.isEmpty(state.line - 1);

        state.blkIndent = oldIndent;
        state.tShift[startLine] = oldTShift;
        state.tight = oldTight;
        state.parentType = oldParentType;

        if (state.renderList) {
            token = state.push('list_item_close', 'li', -1);
            token.markup = String.fromCharCode(markerCharCode);
        }

        nextLine = startLine = state.line;
        itemLines[1] = nextLine;
        contentStart = state.bMarks[startLine];

        if (nextLine >= endLine) {
            break;
        }

        if (state.isEmpty(nextLine)) {
            break;
        }

        // Try to check if list is terminated or continued.
        if (state.tShift[nextLine] < state.blkIndent) {
            break;
        }

        // fail if terminating block found
        terminate = false;
        for (i = 0, l = terminatorRules.length; i < l; i++) {
            if (terminatorRules[i](state, nextLine, endLine, true)) {
                terminate = true;
                break;
            }
        }
        if (terminate) { break; }

        // keep going with original list type if markdown changes
        if (isOrdered) {
            posAfterMarker = skipOrderedListMarker(state, nextLine);
            if (posAfterMarker < 0) {
                posAfterMarker = skipBulletListMarker(state, nextLine);
                if (posAfterMarker < 0) {
                    break;
                }
            }
        } else {
            posAfterMarker = skipBulletListMarker(state, nextLine);
            if (posAfterMarker < 0) {
                posAfterMarker = skipOrderedListMarker(state, nextLine);
                if (posAfterMarker < 0) {
                    break;
                }
            }
        }

        // if there's a space in a previously un-rendered list, start anew
        if (!state.renderList && state.isEmpty(state.line - 1)) {
            break;
        }
    }

    // Finilize list
    if (state.renderList) {
        if (isOrdered) {
            token = state.push('ordered_list_close', 'ol', -1);
            token.markup = String.fromCharCode(markerCharCode);
        } else {
            token = state.push('bullet_list_close', 'ul', -1);
            token.markup = String.fromCharCode(markerCharCode);

        }
        listLines[1] = nextLine;

        // mark paragraphs tight if needed
        if (tight) {
            markTightParagraphs(state, listTokIdx);
        }
    } else {

        // mark everything in the old list hidden
        hideOldListContent(state, listTokIdx);

        // now render everything into one paragraph!
        content = state.getLines(firstStartLine - 1, nextLine, 0, true);

        token = state.push('inline', '', 0);
        token.content = content;
        token.map = [ firstStartLine, nextLine ];
        token.children = [];

        state.push('paragraph_close', 'p', -1);
    }

    state.line = nextLine;
    state.renderList = true;
    return true;
};

// Adopted from https://gist.github.com/gfodor/8394363
(function() {
  var Range, applyToShareJS, requireImpl;

  requireImpl = ace.require != null ? ace.require : require;

  Range = requireImpl('ace/range').Range;

  // Convert an ace delta into an op understood by share.js
  applyToShareJS = function(editorDoc, delta, doc) {
    var getStartOffsetPosition, pos, text;

    // Get the start position of the range, in number of characters
    getStartOffsetPosition = function(range) {
      var i, line, lines, offset, _i, _len;

      lines = editorDoc.getLines(0, range.start.row);
      offset = 0;

      for (i = _i = 0, _len = lines.length; _i < _len; i = ++_i) {
        line = lines[i];
        offset += i < range.start.row ? line.length : range.start.column;
      }

      // Add the row number ot include newlines
      return offset + range.start.row;
    };

    pos = getStartOffsetPosition(delta.range);

    switch (delta.action) {
      case 'insertText':
        doc.insert(pos, delta.text);
        break;
      case 'removeText':
        doc.remove(pos, delta.text.length);
        break;
      case 'insertLines':
        text = delta.lines.join('\n') + '\n';
        doc.insert(pos, text);
        break;
      case 'removeLines':
        text = delta.lines.join('\n') + '\n';
        doc.remove(pos, text.length);
        break;
      default:
        throw new Error('unknown action: ' + delta.action);
    }
  };

  // Attach an ace editor to the document. The editor's contents are replaced
  // with the document's contents unless keepEditorContents is true. (In which
  // case the document's contents are nuked and replaced with the editor's).
  sharejs.Doc.prototype['attachAce'] = function(editor, keepEditorContents) {
    var check, deleteListener, doc, docListener, editorDoc, editorListener, insertListener, offsetToPos, refreshListener, replaceTokenizer, suppress;

    if (!this.provides['text']) {
      throw new Error('Only text documents can be attached to ace');
    }
    doc = this.createContext();

    editorDoc = editor.getSession().getDocument();
    editorDoc.setNewLineMode('unix');

    check = function() {
      return window.setTimeout(function() {
        var editorText, otText;

        editorText = editorDoc.getValue();
        otText = doc.get(); // gfodor
        if (editorText.length !=0  && typeof otText != 'undefined' && editorText !== otText ) {
          console.error('Text does not match!');
          console.error('editor: ' + editorText);
          return console.error('ot:     ' + otText);
          // Should probably also replace the editor text with the doc snapshot
        }
      }, 0);
    };

    if (keepEditorContents) {
      doc.remove(0, doc.get().length); // gfodor
      doc.insert(0, editorDoc.getValue());
    } else {
      editorDoc.setValue(doc.get()); // gfodor
    }

    check();

    // When we apply ops from sharejs, ace emits edit events.
    // These must be ignored to prevent infinite looping.
    suppress = false;

    editorListener = function(change) {
      if (suppress) {
        return;
      }
      applyToShareJS(editorDoc, change.data, doc);
      return check();
    };

    replaceTokenizer = function() {
      var oldGetLineTokens, oldTokenizer;

      oldTokenizer = editor.getSession().getMode().getTokenizer();
      oldGetLineTokens = oldTokenizer.getLineTokens;
      return oldTokenizer.getLineTokens = function(line, state) {
        var cIter, docTokens, modeTokens;

        if ((state == null) || typeof state === 'string') {
          cIter = doc.createIterator(0);
          state = {
            modeState: state
          };
        } else {
          cIter = doc.cloneIterator(state.iter);
          doc.consumeIterator(cIter, 1);
        }
        modeTokens = oldGetLineTokens.apply(oldTokenizer, [line, state.modeState]);
        docTokens = doc.consumeIterator(cIter, line.length);
        if (docTokens.text !== line) {
          return modeTokens;
        }
        return {
          tokens: doc.mergeTokens(docTokens, modeTokens.tokens),
          state: {
            modeState: modeTokens.state,
            iter: doc.cloneIterator(cIter)
          }
        };
      };
    };

    if (doc.getAttributes != null) {
      replaceTokenizer();
    }

    editorDoc.on('change', editorListener);

    docListener = function(op) {
      suppress = true;
      applyToDoc(editorDoc, op);
      suppress = false;
      return check();
    };

    offsetToPos = function(offset) {
      var line, lines, row, _i, _len;

      lines = editorDoc.getAllLines();
      row = 0;
      for (row = _i = 0, _len = lines.length; _i < _len; row = ++_i) {
        line = lines[row];
        if (offset <= line.length) {
          break;
        }
        offset -= lines[row].length + 1;
      }
      return {
        row: row,
        column: offset
      };
    };

    doc.onInsert = function(pos, text) {
      suppress = true;
      editorDoc.insert(offsetToPos(pos), text);
      suppress = false;
      return check();
    };

    doc.onRemove = function(pos, length) {
      suppress = true;
      var range = Range.fromPoints(offsetToPos(pos), offsetToPos(pos + length));
      editorDoc.remove(range);
      suppress = false;
      return check();
    };

    doc.onRefresh = function(startoffset, length) {
      var range = Range.fromPoints(offsetToPos(startoffset), offsetToPos(startoffset + length));
      return editor.getSession().bgTokenizer.start(range.start.row);
    };

    doc.detach = function() {
      editorDoc.removeListener('change', editorListener);
      return delete doc.detach;
    };

  };

}).call(this);

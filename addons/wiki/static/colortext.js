'use strict';

import { $inputRule, $command, $markSchema, $remark } from '@milkdown/utils';
import { markRule } from '@milkdown/prose';
import { toggleMark } from '@milkdown/prose/commands';
import { flatMap, isLiteral } from './utils.js';

export const colortextSchema = $markSchema('colortext', function () {
  return {
      parseDOM: [
          {
              tag: 'span[style]',
              getAttrs: (dom) => {
                  const color = dom.style.color;
                  return color ? { color } : false;
              },
          },
      ],
      attrs: {
          color: { default: null },
      },
      toDOM: mark => ['span', { style: `color: ${mark.attrs.color}` }, 0],
      parseMarkdown: {
          match: node => node.type === 'colortext',
          runner: (state, node, markType) => {
              state.openMark(markType, { color: node.color });
              state.next(node.children);
              state.closeMark(markType);
          }
      },
      toMarkdown: {
          match: mark => mark.type.name === 'colortext',
          runner: (state, mark) => {
              state.withMark(mark, 'colortext', undefined, { color: mark.attrs.color });
          }
      }
  };
});

export const colortextInputRule = $inputRule(function (ctx) {
  return markRule(/<span\s+style=['"]color:\s*([^;'"]+?)['"][^>]*>([^<]+)<\/span>/i, colortextSchema.type(ctx), {
      getAttr: match => ({ color: match[1] })
  });
});

export const remarkColortextToMarkdown = $remark('remarkColortextToMarkdown', function () { return colortextToMarkdownPlugin; });

export const remarkColortextFromMarkdown = $remark('remarkColortextFromMarkdown', function () { return colortextFromMarkdownPlugin; });

export const toggleColortextCommand = $command('ToggleColortext', ctx => {
  return function(color) {
      if (!color)
          return;
      var attrs = { color: color };
      return toggleMark(colortextSchema.type(ctx), attrs);
  };
});

const colortextFromMarkdownPlugin = function colortextFromMarkdownPlugin() {
  function transformer(tree) {
      return flatMap(tree, function(node) {

          if (node.type === 'code' || node.type === 'code_block') return [node];
          if (node.type === 'inlineCode') return [node];

          if (!isLiteral(node)) return [node];

          const value = node.value;
          const output = [];
          const regex = /<span style="(.*?)">(.*?)<\/span>/g;
          let match;
          let str = value;
          let lastIndex = 0;

          while ((match = regex.exec(str))) {
              const { index } = match;
              const style = match[1];
              const styleContext = match[2];
              const color = style.match(/color:\s*([^;]+);?/i)?.[1] || '';
              const colortext = color && styleContext;

              if (index > lastIndex) {
                  output.push({
                      ...node,
                      value: str.slice(lastIndex, index),
                  });
                  const lastElement = output[output.length - 1];
                  if (node.position) {
                      lastElement.position = {
                          start: {
                              line: node.position.start.line,
                              column: node.position.start.column + lastIndex,
                              offset: node.position.start.offset + lastIndex
                          },
                          end: {
                              line: node.position.start.line,
                              column: node.position.start.column + index,
                              offset: node.position.start.offset + index
                          }
                      };
                  }
              }

              if (colortext) {
                  const colortextNode = {
                      type: 'colortext',
                      color: color,
                      children: [
                          {
                              type: 'text',
                              value: colortext,
                          }
                      ]
                  };
                  if (node.postion){
                      colortextNode['position'] = {
                          start: {
                              line: node.position.start.line,
                              column: node.position.start.column + index,
                              offset: node.position.start.offset + index
                          },
                          end: {
                              line: node.position.start.line,
                              column: node.position.start.column + index + match[0].length,
                              offset: node.position.start.offset + index + match[0].length
                          }
                      };
                      colortextNode.children['postion'] = {
                          start: {
                              line: node.position.start.line,
                              column: node.position.start.column + index + match[0].indexOf(colortext),
                              offset: node.position.start.offset + index + match[0].indexOf(colortext)
                          },
                          end: {
                              line: node.position.start.line,
                              column: node.position.start.column + index + match[0].indexOf(colortext) + colortext.length,
                              offset: node.position.start.offset + index + match[0].indexOf(colortext) + colortext.length
                          }
                      };
                  }
                  output.push(colortextNode);
              }

              lastIndex = index + match[0].length;
              regex.lastIndex = lastIndex;
          }

          if (lastIndex < value.length) {
              output.push({
                  ...node,
                  value: value.slice(lastIndex)
              });
          }

          return output;
      });
  }
  return transformer;
};

const handleColortext = function handleColortext(node, _, state, info) {
  const tracker = state.createTracker(info);
  const exit = state.enter('colortext');
  let value = tracker.move('\\<span style="color: ' + node.color + '">');
  value += state.containerPhrasing(node, {
    ...tracker.current()
  });
  value += '\\</span>';
  
  exit();
  return value;
};

const colortextToMarkdown = function colortextToMarkdown() {
  return {
    unsafe: [
      {
        character: '<span style="color: ',
        inConstruct: 'phrasing'
      },
      {
        character: '</span>',
        inConstruct: 'phrasing'
      }
    ],
    handlers: {
      colortext: handleColortext
    }
  };
};

var colortextToMarkdownPlugin = function colortextToMarkdownPlugin() {
  var self = this;
  var data = self.data();

  var toMarkdownExtensions =
    data.toMarkdownExtensions || (data.toMarkdownExtensions = []);

  toMarkdownExtensions.push(colortextToMarkdown());
};

'use strict';
import { $inputRule, $command, $markSchema, $remark} from '@milkdown/utils';
import { markRule } from '@milkdown/prose';
import { toggleMark } from '@milkdown/prose/commands';
import { flatMap, isLiteral } from './utils.js';

export const underlineSchema = $markSchema('underline', function () {
    return {
        parseDOM: [
            { tag: 'u' },
            { style: 'text-decoration', getAttrs: value => value === 'underline' ? {} : false },
        ],
        toDOM: () => ['u', 0],
        parseMarkdown: {
            match: node => node.type === 'underline',
            runner: (state, node, markType) => {
                state.openMark(markType);
                state.next(node.children);
                state.closeMark(markType);
            }
        },
        toMarkdown: {
            match: mark => mark.type.name === 'underline',
            runner: (state, mark) => {
                state.withMark(mark, 'underline');
            }
        }
    };
});

export const underlineInputRule = $inputRule(function (ctx) {
    return markRule(/<u>(.*?)<\/u>/, underlineSchema.type(ctx));
});

export const remarkUnderlineToMarkdown = $remark('remarkUnderlineToMarkdown', function () { return underlineToMarkdownPlugin; });

export const remarkUnderlineFromMarkdown = $remark('remarkUnderlineFromMarkdown', function () { return underlineFromMarkdownPlugin; });

export const toggleUnderlineCommand = $command('ToggleUnderline', ctx => () => {
  return toggleMark(underlineSchema.type(ctx));
});

const underlineFromMarkdownPlugin = function underlineFromMarkdownPlugin() {
    function transformer(tree) {
      return flatMap(tree, function(node) {

        if (node.type === 'code' || node.type === 'code_block') return [node];
        if (node.type === 'inlineCode') return [node];

        if (!isLiteral(node)) return [node];

        const value = node.value;
        const output = [];
        const regex = /<u>(.*?)<\/u>/g;
        let match;
        let str = value;
        let lastIndex = 0;

        while ((match = regex.exec(str))) {
          const { index } = match;
          const underlineText = match[1];

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

          if (underlineText) {
            const underlineNode = {
              type: 'underline',
              children: [
                {
                  type: 'text',
                  value: underlineText,
                }
              ]
            };
            if (node.postion){
              underlineNode['position'] = {
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
              underlineNode.children['postion'] = {
                start: {
                  line: node.position.start.line,
                  column: node.position.start.column + index + 3,
                  offset: node.position.start.offset + index + 3
                },
                end: {
                  line: node.position.start.line,
                  column: node.position.start.column + index + 3 + underlineText.length,
                  offset: node.position.start.offset + index + 3 + underlineText.length
                }
              };
            }
            output.push(underlineNode);
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

const constructsWithoutUnderline = [
    'autolink',
    'destinationLiteral',
    'destinationRaw',
    'reference',
    'titleQuote',
    'titleApostrophe'
  ];

const underlineToMarkdown = function underlineToMarkdown() {
    return {
      unsafe: [
        {
          character: '<u>',
          inConstruct: 'phrasing',
          notInConstruct: constructsWithoutUnderline
        },
        {
          character: '</u>',
          inConstruct: 'phrasing',
          notInConstruct: constructsWithoutUnderline
        }
      ],
      handlers: {underline: handleUnderline}
    };
  };

const handleUnderline = function handleUnderline(node, _, state, info) {
    const tracker = state.createTracker(info);
    const exit = state.enter('underline');
    let value = tracker.move('\\<u>');
    value += state.containerPhrasing(node, {
      ...tracker.current()
    });
    value += tracker.move('\\</u>');
    exit();
    return value;
};

var underlineToMarkdownPlugin = function underlineToMarkdownPlugin() {
    var self = this;
    var data = self.data();

    var toMarkdownExtensions =
      data.toMarkdownExtensions || (data.toMarkdownExtensions = []);

    toMarkdownExtensions.push(underlineToMarkdown());
  };

'use strict';
import { $inputRule, $command } from '@milkdown/utils';
import { InputRule } from '@milkdown/prose/inputrules';
import { findSelectedNodeOfType } from '@milkdown/prose';
import * as mCommonmark from '@milkdown/preset-commonmark';

export const extendedImageSchemaPlugin = mCommonmark.imageSchema.extendSchema((prevSchema) => {
  return (ctx) => {
      return {
          ...prevSchema(ctx),
          attrs: {
              ...prevSchema(ctx).attrs,
              width: { default: '' },
              height: { default: '' },
          },
          parseDOM: [
              ...prevSchema(ctx).parseDOM,
              {
                  tag: 'img[src]',
                  getAttrs: (dom) => {
                      if (!(dom instanceof HTMLElement)) throw new Error('Expected HTMLElement');
                      return {
                          ...prevSchema(ctx).parseDOM[0].getAttrs(dom),
                          width: dom.getAttribute('width') || '',
                          height: dom.getAttribute('height') || '',
                      };
                  },
              },
          ],
          parseMarkdown: {
              ...prevSchema(ctx).parseMarkdown,
              runner: (state, node, type) => {
                  const [url, size] = node.url.split(/\s+(.+)$/);
                  const sizeMatch = size && size.match(/^=([\d]+%?)x?([\d]*%?)$/);
                  var width = '';
                  var height = '';

                  if (sizeMatch) {
                      width = sizeMatch[1];
                      height = sizeMatch[2];
                  }
                  const alt = node.alt;
                  const title = node.title;
                  state.addNode(type, {
                      src: url,
                      alt,
                      title,
                      width,
                      height
                  });
              },
          },
          toMarkdown: {
              ...prevSchema(ctx).toMarkdown,
              runner: (state, node) => {
                  var url = node.attrs.src;   
            
                  if (node.attrs.width || node.attrs.height) {
                      const width = node.attrs.width ? `=${node.attrs.width}` : '';
                      const height = node.attrs.height ? `${node.attrs.height}` : '';
                      url += ` ${height ? `${width}x${height}` : width}`;
                  }              
                  state.addNode('image', undefined, undefined, {
                      title: node.attrs.title,
                      url,
                      alt: node.attrs.alt,
                      width: node.attrs.width,
                      height: node.attrs.height,
                  });
              },
          },
      };
  };
});

export const extendedInsertImageCommand = $command('ExtendedIpdateImage', ctx => {
    return function(payload) {
        return function(state, dispatch) {
            if (!dispatch)
                return true;
      
            const { src = '', alt = '', title = '', width = '' } = payload;
      
            const node = mCommonmark.imageSchema.type(ctx).create({ src, alt, title, width });
            if (!node)
                return true;
      
            dispatch(state.tr.replaceSelectionWith(node).scrollIntoView());
            return true;
        };
    };
});

export const extendedUpdateImageCommand = $command('ExtendedUpdateImage', ctx => {
    return function(payload) {
        return function(state, dispatch) {
            const nodeWithPos = findSelectedNodeOfType(state.selection, mCommonmark.imageSchema.type(ctx));
            if (!nodeWithPos)
                return false;
          
            const { node, pos } = nodeWithPos;
          
            var newAttrs = Object.assign({}, node.attrs);
            const { src, alt, title, width } = payload;
            if (src !== undefined)
                newAttrs.src = src;
            if (alt !== undefined)
                newAttrs.alt = alt;
            if (title !== undefined)
                newAttrs.title = title;
            if (width !== undefined)
                newAttrs.width = width;
          
            dispatch?.(state.tr.setNodeMarkup(pos, undefined, newAttrs).scrollIntoView());
            return true;
        };
    };
});

export const updatedInsertImageInputRule = $inputRule(function (ctx) {
    const imagePattern = /!\[(?<alt>[^\]]*)\]\((?<src>[^\s)]+)(?:\s+"(?<title>[^"]*)")?(?:\s+=\s*(?<width>\d+(?:%|x)?)(?:x(?<height>\d*(?:%)?))?)?\)/;

    return new InputRule(imagePattern, (state, match, start, end) => {
        if (!match) return null;

        const { alt, src, title, width, height } = match.groups;

        const attrs = { src, alt, title };

        if (width) {
            if (width.endsWith('x')) {
                attrs.width = width.slice(0, -1);
            } else {
                attrs.width = width;
            }
        }
        if (height) attrs.height = height;

        const { tr } = state;
        const nodeType = mCommonmark.imageSchema.type(ctx);

        return tr.replaceWith(start, end, nodeType.create(attrs));
    });
});

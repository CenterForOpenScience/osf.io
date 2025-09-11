'use strict';

import { $inputRule } from '@milkdown/utils';
import { InputRule } from '@milkdown/prose/inputrules';
import * as mCommonmark from '@milkdown/preset-commonmark';

export const linkInputRuleCosutom = $inputRule((ctx) => {
    const linkPattern = /(?<!\\|!)\[(?!!\[.*?\]\(.*?\))(.+?(?<!\\)(?:\\\\)*)\]\((.+?)(?:\s+['"](.+?)['"])?\)/;
    return new InputRule(linkPattern, (state, match, start, end) => {
        if (!match) return null;

        var [okay, text, href] = match;
        const { tr } = state;
        const markType = mCommonmark.linkSchema.type(ctx);

        if (!markType) return null;

        if (text === "\ufffc") {
            const node = state.doc.nodeAt(start + 1);
            if (node.type.name === "image") {
                const imageAttrs = {
                    src: node.attrs.src,
                    alt: node.attrs.alt,
                    title: node.attrs.title,
                    link: href,
                    width: node.attrs.width,
                    height: node.attrs.height
                };
                const linkMark = markType.create({ href });
                const imageNode = mCommonmark.imageSchema.type(ctx).create(imageAttrs);
                const imageWithLink = imageNode.mark([linkMark]);
                tr.replaceWith(start, end, imageWithLink);
            }
        } else {
            tr.removeMark(start, end);
            tr.insertText(text, start, end);
            tr.addMark(start, start + text.length, markType.create({ href }));
        }
        return tr;
    });
});

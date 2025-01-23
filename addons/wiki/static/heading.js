'use strict';

export function customHeadingIdGenerator(node) {
    return node.textContent
        .toLowerCase()
        .replace(/[^\p{L}\p{N}._:;-]/gu, '')
        .replace(/\s+/g, '')
        .trim();
}

'use strict';

function isParent(node) {
    return !!(node && node.children && Array.isArray(node.children));
  }
  
export function isLiteral(node) {
    return !!(node && typeof node.value === 'string');
  }

export function flatMap(ast, fn) {
    return transform(ast, 0, null)[0];

    function transform(node, index, parent) {
        console.log('aa');
        if (isParent(node)) {
            const out = [];
            for (var i = 0, n = node.children.length; i < n; i++) {
                const nthChild = node.children[i];
                if (nthChild) {
                    if (nthChild.type === 'text' && /.*!\[.*\]\($/.test(nthChild.value)) {
                        const remainingChildren = getRemainingNode(i, node.children);
                        const transformedChildren = transformImageSection(remainingChildren);
                        out.push(...transformedChildren)
                        break;
                    } else {
                        addTransformedChildren(nthChild, i, node, out);
                    }
                }
            }
            node.children = out;
        }
        return fn(node, index, parent);
    }

    function addTransformedChildren(nthChild, i, node, out) {
        const xs = transform(nthChild, i, node);
        if (xs) {
            for (var j = 0, m = xs.length; j < m; j++) {
                const item = xs[j];
                if (item) out.push(item);
            }
        }
    }

  function transformImageSection(remainingChildren) {
      const result = [];
      for (var i = 0; i < remainingChildren.length; i++) {
          if (remainingChildren[i].type === 'text' && /!\[.*\]\($/.test(remainingChildren[i].value)) {
              const imageNode = createImageNode(remainingChildren[i], remainingChildren[i + 1], remainingChildren[i + 2]);
              if (imageNode) {
                  result.push(imageNode);
                  i += 2;
              } else {
                result.push(remainingChildren[i]);
            }
          } else {
              result.push(remainingChildren[i]);
          }
      }
      return result;
  }

  function getRemainingNode(startIdx, nodeChildren) {
      var remainingChildren = [];
      for (var i = startIdx; i < nodeChildren.length; i++) {
          if (nodeChildren[i].type === 'text') {
              if (nodeChildren[i].value.match(/.*!\[.*\]\($/)) {
                  const matchBeforeImage = nodeChildren[i].value.match(/^(.*?)(!\[.*\]\()$/);
                  if (matchBeforeImage[1] !== '') {
                      const beforeImage = matchBeforeImage[1];
                      const matchSize = beforeImage.match(/^(\s*=\d+\))(.*)$/);
                      if (matchSize) {
                          if (matchSize[1] !== '') {
                              remainingChildren.push({ type: 'text', value: matchSize[1] });
                          }
                          if (matchSize[2] !== '') {
                              remainingChildren.push({ type: 'text', value: matchSize[2] });
                          }
                      } else {
                          remainingChildren.push({ type: 'text', value: beforeImage });
                      }
                  }
                  remainingChildren.push({ type: 'text', value: matchBeforeImage[2] });
                  continue;
              } else if (nodeChildren[i].value.match(/^(\s*=\d+\))(.*)/)) {
                  const match = nodeChildren[i].value.match(/^(\s*=\d+\))(.*)/);
                  if (match) {
                      if (match[1] !== '') {
                          remainingChildren.push({ type: 'text', value: match[1] });
                      }
                      if (match[2] !== '') {
                          remainingChildren.push({ type: 'text', value: match[2] });
                      }
                  }
                  continue;
              }
          }
          remainingChildren.push(nodeChildren[i])
      }
      return remainingChildren;
  }
}

function createImageNode(altNode, linkNode, sizeNode) {
    const altTextMatch = altNode.value.match(/^!\[(.*)\]\($/);
    const imageNode = { type: 'image', alt: altTextMatch ? altTextMatch[1] : '', url: '' };

    if (linkNode && linkNode.type === 'link') {
        imageNode.url = linkNode.url;
    }

    if (sizeNode && sizeNode.type === 'text' && /^\s*=\d+%?(x\d*%?)?\)?\s*$/.test(sizeNode.value)) {
        const sizeValue = sizeNode.value.replace(/\)$/, '');
        imageNode.url += sizeValue;
    } else {
        return null;
    }

    return imageNode;
}

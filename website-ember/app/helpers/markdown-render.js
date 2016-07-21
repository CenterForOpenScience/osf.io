import Ember from 'ember';
import markdown from 'npm:markdown';

const { String: EmString, isEmpty } = Ember;

const { htmlSafe } = EmString;

/**
 * Helper to render markdown snippets.
 *   Adapted from https://github.com/greenfieldhq/ember-markdown-it/blob/master/addon/helpers/markdown-render.js
 * @class markdown-render
 */
export function markdownRender(params) {
    // TODO: This implements full-render mode (suitable for all OSF use cases except some of wiki)
  if (isEmpty(params)) {
    return;
  }

  let [markdownString] = params;
  let html = markdown.full.render(markdownString);

  return htmlSafe(html);
}

export default Ember.Helper.helper(markdownRender);

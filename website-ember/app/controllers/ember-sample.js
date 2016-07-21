import Ember from 'ember';

import MarkdownIt from 'npm:markdown-it';

let md = new MarkdownIt();
var result = md.render('# markdown-it rulezz!');

export default Ember.Controller.extend({
    markdownText: result,
});

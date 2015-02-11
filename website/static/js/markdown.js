var markdown = require('markdown-it')('commonmark')
    .use(require('markdown-it-video'))
    .use(require('markdown-it-sanitizer'));

module.exports = markdown;
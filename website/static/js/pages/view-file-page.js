var $ = require('jquery');
require('../../vendor/bower_components/jquery.tagsinput/jquery.tagsinput.css');
require('jquery-tagsinput');


    // Tag input
    $('#node-tags').tagsInput({
        width: '100%',
        interactive: window.contextVars.currentUser.canEdit,
        maxChars: 128,
        onAddTag: function(tag){
            var url = window.contextVars.node.urls.api + 'addtag/' + tag + '/';
            console.log(url);
            var request = $.ajax({
                url: url,
                type: 'POST',
                contentType: 'application/json'
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Failed to add tag', {
                    tag: tag, url: url, textStatus: textStatus, error: error
                });
            });
        },
        onRemoveTag: function(tag){
            var url = window.contextVars.node.urls.api + 'removetag/' + tag + '/';
            var request = $.ajax({
                url: url,
                type: 'POST',
                contentType: 'application/json'
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Failed to remove tag', {
                    tag: tag, url: url, textStatus: textStatus, error: error
                });
            });
        }
    });

    // Limit the maximum length that you can type when adding a tag
    $('#node-tags_tag').attr('maxlength', '128');

    // Wiki widget markdown rendering
    if (ctx.wikiWidget) {
        // Render math in the wiki widget
        var markdownElement = $('#markdownRender');
        mathrender.mathjaxify(markdownElement);

        // Render the raw markdown of the wiki
        if (!ctx.usePythonRender) {
            var request = $.ajax({
                url: ctx.urls.wikiContent
            });
            request.done(function(resp) {
                var rawText = resp.wiki_content || '*No wiki content*';
                var renderedText = md.render(rawText);
                var truncatedText = $.truncate(renderedText, {length: 400});
                markdownElement.html(truncatedText);
                mathrender.mathjaxify(markdownElement);
            });
        }
    }

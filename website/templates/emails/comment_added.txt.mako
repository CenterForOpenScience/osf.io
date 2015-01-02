Hello ${name},

    ${commenter} ${'replied to ' + (parent_comment['commenter'] + '\'s' if parent_comment['commenter'] != name else 'your ') + 'comment \"' + parent_comment['content'] + '\"' if parent_comment else 'commented'} on your project "${title}":

    "${content}"

    From the Open Science Framework

<%page expression_filter="h"/>

% if user['can_edit']:
<nav class="navbar navbar-default wiki-status-sm wiki-status-lg">
    <div class="navbar-collapse">
        <ul class="superlist nav navbar-nav">
            <li><a href="#" data-toggle="modal" data-target="#newWiki">New</a></li>
                <%include file="add_wiki_page.mako"/>
            <li><a href="${urls['web']['edit']}">Edit</a></li>
            % if wiki_id and wiki_name != 'home':
            <li><a href="#" data-toggle="modal" data-target="#deleteWiki">Delete</a></li>
                <%include file="delete_wiki_page.mako"/>
            % endif
        </ul>
    </div>
</nav>
% endif

<h3 class="wiki-title wiki-title-xs" id="wikiName">
    % if wiki_name == 'home':
        <i class="icon-home"></i>
    % endif
    <span id="pageName"
        % if wiki_name == 'home' and not node['is_registration']:
            data-toggle="tooltip"
            title="Note: Home page cannot be renamed."
        % endif
        >${wiki_name if wiki_name != 'home' else 'Home'}</span>
</h3>

<script type="text/javascript">
    var $pageName = $('#pageName');
    $pageName.tooltip();

    // Activate editable title unless on home page or in edit mode only for users that can edit
    %if 'write' in user['permissions'] and not is_edit and wiki_id and wiki_name != 'home' and not node['is_registration']:
    $(document).ready(function() {
        $.fn.editable.defaults.mode = 'inline';
        $pageName.editable({
            type: 'text',
            send: 'always',
            url: '${urls['api']['rename']}',
            ajaxOptions: {
               type: 'put',
               contentType: 'application/json',
               dataType: 'json'
            },
            validate: function(value) {
                if($.trim(value) == ''){
                    return 'The wiki page name cannot be empty.';
                } else if(value.length > 100){
                    return 'The wiki page name cannot be more than 100 characters.';
                }
            },
            params: function(params) {
                return JSON.stringify(params);
            },
            success: function(response, value) {
                window.location.href = '${urls['web']['base']}' + encodeURIComponent(value) + '/';
            },
            error: function(response) {
                var msg = response.responseJSON.message_long;
                if (msg) {
                    return msg;
                } else {
                    // Log unexpected error with Raven
                    Raven.captureMessage('Error in renaming wiki', {
                        url: '${urls['api']['rename']}',
                        responseText: response.responseText,
                        statusText: response.statusText
                    });
                    return 'An unexpected error occurred. Please try again.';
                }
            }
        });
    });
    %endif
</script>

<%page expression_filter="h"/>



<h3 class="wiki-title wiki-title-xs" id="wikiName">
    % if wiki_name == 'home':
        <i class="icon-home"></i>
    % endif
    <span id="pageName"
        % if wiki_name == 'home' and not node['is_registration']:
            data-bind="tooltip: {title: 'Note: Home page cannot be renamed.'}"
        % endif
    >${wiki_name if wiki_name != 'home' else 'Home'}</span>
</h3>

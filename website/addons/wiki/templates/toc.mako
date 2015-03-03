<%page expression_filter="h"/>

<div class="osf-sidenav hidden-print wiki-sidenav" role="complementary">

    <h4 class="node-category">
        <div class="row">
            <div class="col-xs-10">
                ${node['category'].title()} Wiki Pages
            </div>
            <div class="col-xs-2">
                % if user['can_edit']:
                    <a href="#" data-toggle="modal" data-target="#newWiki">
                        <i class="icon icon-plus-sign pointer icon-lg" data-toggle="tooltip" title="New" data-placement="left"></i>
                    </a>
                % endif
            </div>
        </div>
    </h4>

    
        <ul class="nav bs-sidenav" style="margin: 0;">
            <li
                %if wiki_name == 'home':
                    class="active"
                %endif
            >
                <div class="row">
                    ## NOTE: Do NOT use web_url_for here because we want to use the GUID urls for these links
                    <a href="${urls['web']['home']}">
                        <div class="col-xs-12">Home</div>
                    </a>
                </div> 
            </li>
            % for page in pages_current:
                %if page['name'] != 'home':
                    <li ${'class="active"' if page['name'] == wiki_name else '' | n}>
                            <div class="row">
                                %if page['name'] == wiki_name and user['can_edit']:
                                    <a href="${page['url']}"><div class="col-xs-10">${page['name']}</div></a>
                                    <div class="col-xs-2">
                                        <a href="#" data-toggle="modal" data-target="#deleteWiki">
                                            <i class="icon icon-trash text-danger pointer icon-lg" data-toggle="tooltip" title="Delete" data-placement="left"> </i>
                                        </a>
                                    </div>
                                % else:
                                    <a href="${page['url']}"><div class="col-xs-12">${page['name']}</div></a>
                                % endif
                            </div>
                    </li>
                % endif
            %endfor
           
        </ul>
        % if category == 'project':
        <hr />
        <h4>Component Wiki Pages</h4>
            <ul class="nav bs-sidenav" style="margin: 0;">
            % for child in toc:
                <li>
                    <div class="row">
                        <div class="col-xs-10">
                            <a href="${child['url']}">
                                % if child['is_pointer']:
                                    <i class="icon icon-link"></i>
                                % endif
                                ${child['title'] | n}
                                    % if child['category']:
                                        (${child['category']})
                                    % endif
                            </a>
                        </div>
                    </div>
                    <ul class="wiki-component">
                        % for child_page in child['pages_current']:
                            % if child_page['name'] != 'home':
                                <li>
                                    <a href="${child_page['url']}">${child_page['name']}</a>
                                </li>
                            % endif
                        % endfor
                    </ul>
                </li>
            % endfor
            </ul>
        %endif
</div>

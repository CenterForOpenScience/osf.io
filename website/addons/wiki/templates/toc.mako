<%page expression_filter="h"/>

<div class="osf-sidenav hidden-print wiki-sidenav" role="complementary">

    <h4 class="node-category">
        <div class="row">
            <div class="col-xs-10">
                ${node['category'].title()} Wiki Pages
            </div>
        </div>
        % if user['can_edit']:
            <div class="row">
                <div class="col-xs-2 wiki-sidenav">
                    <a href="#" data-toggle="modal" data-target="#newWiki">
                        <i class="fa fa-plus-circle pointer fa-lg wiki-menu" data-toggle="tooltip" title="New" data-placement="top"></i>
                    </a>
                </div>
            </div>
        % endif
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
                        %if page['name'] == wiki_name and user['can_edit']:
                            <div class="row">
                                <a href="${page['url']}"><div class="col-xs-8">${page['name']}</div></a>
                                <div class="col-xs-2">
                                    <i class="fa fa-cog pointer fa-lg" data-toggle="tooltip"
                                       title="Settings" data-placement="left"
                                       data-bind="toggle: subsVisible"> </i>
                                </div>
                                <div class="col-xs-2">
                                    <a href="#" data-toggle="modal" data-target="#deleteWiki">
                                        <i class="fa fa-trash-o text-danger pointer fa-lg" data-toggle="tooltip" title="Delete" data-placement="left"> </i>
                                    </a>
                                </div>
                            </div>
                            <div class="option-cloud" data-bind="visible: subsVisible">
                                <div class="title" data-bind="text: subText"></div>
                                <div class="container" data-bind="foreach: subList">
                                    <div class="cloud-option pointer" data-bind='css: { current: value === $root.subscription().value },
                                                                                 click: $root.clickSub.bind(value)'>
                                        <span data-bind="text: text"></span>
                                    </div>
                                </div>
                            </div>
                        % else:
                            <div class="row">
                                    <a href="${page['url']}"><div class="col-xs-12">${page['name']}</div></a>
                            </div>
                        % endif
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
                            <i class="fa fa-hand-o-right"></i>
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

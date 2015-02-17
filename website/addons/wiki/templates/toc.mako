<%page expression_filter="h"/>

<div class="osf-sidenav hidden-print wiki-sidenav" role="complementary">

    <h4 class="node-category"> ${node['category'].title()} Wiki Pages <a href="#" data-toggle="modal" class="btn btn-success-alt btn-sm" data-target="#newWiki" > <i class="icon-plus"></i> New</a>
 </h4> 

    
        <ul class="nav bs-sidenav" style="margin: 0;">
            <li
                %if wiki_name == 'home':
                    class="active"
                %endif
            >
                <div class="row">
                    <div class="col-xs-12">
                        ## NOTE: Do NOT use web_url_for here because we want to use the GUID urls for these links
                        <a href="${urls['web']['home']}">Home</a>
                    </div>
                </div> 
            </li>
            % for page in pages_current:
                %if page['name'] != 'home':
                    %if page['name'] == wiki_name:
                    <li class="active"> 
                        <div class="row">
                            <div class="col-xs-10"><a href="${page['url']}">${page['name']}</a></div>
                            <div class="col-xs-2">
                                <a href="#" data-toggle="modal" data-target="#deleteWiki">
                                    <i class="icon icon-trash text-danger pointer icon-lg"> </i>
                                </a>
                            </div>
                        </div>                        
                    </li>
                    % else:
                    <li> 
                        <div class="row">
                            <div class="col-xs-12"><a href="${page['url']}">${page['name']}</a></div>
                        </div>                        
                    </li>
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

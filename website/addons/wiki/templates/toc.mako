<%page expression_filter="h"/>

<div class="osf-sidenav hidden-print" role="complementary">

    <ul class="nav bs-sidenav" style="margin: 0;">

        <h4 style="margin-left: 10px;" class="node-category"> ${node['category'].title()} Wiki Pages</h4>
            <li>
                ## NOTE: Do NOT use web_url_for here because we want to use the GUID urls for these links
                <a href="${urls['web']['home']}">Home</a>
            </li>
            % for page in pages_current:
                %if page['name'] != 'home':
                    <li>
                        ## Again, do not use web_url_for here either
                        <a href="${page['url']}">${page['name']}</a>
                    </li>
                % endif
            %endfor

        % if category == 'project':

        <hr />
        <h4 style="margin-left: 10px;">Component Wiki Pages</h4>

            % for child in toc:
                <li>
                    <a href="${child['url']}">
                        % if child['is_pointer']:
                            <i class="icon-hand-right"></i>
                        % endif

                        ${child['title'] | n}
                            % if child['category']:
                                (${child['category']})
                            % endif
                    </a>

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

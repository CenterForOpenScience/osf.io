<div class="osf-sidenav hidden-print" role="complementary">

    <ul class="nav bs-sidenav" style="margin: 0;">

        <h4 style="margin-left: 10px;" class="node-category"> ${node['category'].title()} Wiki Pages</h4>
            <li>
                ## NOTE: Do NOT use web_url_for here because we want to use the GUID urls for these links
                <a href="${web_urls['home']}">${'home'}</a>
            </li>
            % for page_name, page_web_url in pages_current:
                %if page_name != 'home':
                    <li>
                        ## Again, do not use web_url_for here either
                        <a href="${page_web_url}">${page_name}</a>
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

                        ${child['title']}
                            % if child['category']:
                                (${child['category']})
                            % endif
                    </a>

                    <ul style="list-style-type: none;">
                        % for child_page_name, child_page_web_url in child['pages_current']:
                            % if k != 'home':
                                <li class="">
                                    <a href="${child_page_web_url}">${child_page_name}</a>
                                </li>
                            % endif
                        % endfor
                    </ul>
                </li>
            % endfor
        </ul>
   %endif
</div>

<div class="osf-sidenav hidden-print" role="complementary">

    <ul class="nav bs-sidenav" style="margin: 0;">

        <h4 style="margin-left: 10px;" class="node-category"> ${node['category'].title()} Wiki Pages</h4>
            <li>
                ## NOTE: Do NOT use web_url_for here because we want to use the GUID urls for these links
                <a href="${wiki_home_web_url}">${'home'}</a>
            </li>
            % for page_name in pages_current:
                %if page_name != 'home':
                    <li>
                        ## Again, do not use web_url_for here either
                        <a href="${node['url']}wiki/${page_name | u}/">${page_name}</a>
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
                        % for k in child['pages']:
                            % if k != 'home':
                                <li class="">
                                    <a href="/${node['id']}/node/${child['id']}/wiki/${k}">${k}</a>
                                </li>
                            % endif
                        % endfor
                    </ul>
                </li>
            % endfor
        </ul>
   %endif
</div>

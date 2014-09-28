<div class="osf-sidenav hidden-print" role="complementary">

    <ul class="nav bs-sidenav" style="margin: 0;">

        <h4 style="margin-left: 10px;" class="node-category"> ${node['category'].title()} Wiki Pages</h4>
            <li>
                <a href=${web_url_for('project_wiki_page', wid='home', pid=node['id'])}>${'home'}</a>
            </li>
            % for k in pages_current:
                %if k != 'home':
                    <li>
                        <a href=${web_url_for('project_wiki_page', wid=k, pid=node['id'])}>${k}</a>
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

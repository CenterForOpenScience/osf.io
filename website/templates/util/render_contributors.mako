% for contributor in contributors:
    <span data-pk="${contributor['id']}"
            class="contributor
                ${'contributor-registered' if contributor['registered'] else 'contributor-unregistered'}
                ${'contributor-self' if user['id'] == contributor['id'] else ''}">
        % if contributor['registered']:
        <a href="/${contributor['id']}/">${contributor['fullname']}</a>
        % else:
        <span>${contributor['fullname']}</span>
        %endif
        % if ('admin' in user['permissions'] or user['id'] == contributor['id']) and not node['is_registration']:
            <span
                    class="btn-remove"
                    data-userid="${contributor['id']}"
                    data-fullname="${contributor['fullname']}"
                ><i class="icon-remove"></i>
            </span>
        % endif
    </span>
    ${'' if loop.last else '|'}
% endfor

% for contributor in contributors:
    <span data-pk="${contributor['id']}"
        class="contributor ${'contributor-registered' if contributor['registered'] else 'contributor-unregistered'}">
        <a href="/${contributor['id']}/"
            % if 'admin' in user['permissions'] or user['id'] == contributor['id']:
                class="user-quickedit "
                data-userid="${contributor['id']}" data-fullname="${contributor['fullname']}"
            % endif
            >${contributor['fullname']}</a>${', ' if not loop.last else ''}
    </span>
% endfor

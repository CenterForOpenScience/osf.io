% for contributor in contributors:
    <li data-pk="${contributor['id']}"
            class="contributor
                ${'contributor-registered' if contributor['registered'] else 'contributor-unregistered'}
                ${'contributor-self' if user['id'] == contributor['id'] else ''}">
        % if contributor['registered']:
        <a class='user-profile' href="/${contributor['id']}/">${contributor['fullname']}</a></li>
        % else:
        <span>${contributor['fullname']}</span></li>
        %endif
% endfor

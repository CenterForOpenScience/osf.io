% for contributor in contributors:
    <li data-pk="${contributor['id']}"
            class="contributor
                ${'contributor-registered' if contributor['registered'] else 'contributor-unregistered'}
                ${'contributor-self' if user['id'] == contributor['id'] else ''}">
        <%
            condensed = contributor['fullname']
            is_condensed = False
            if len(condensed) >= 50:
                condensed = condensed[:23] + "..." + condensed[-23:]
                is_condensed = True
        %>
        % if contributor['registered']:
            <a class='user-profile' rel="${'tooltip' if is_condensed else ''}" title="${contributor['fullname']}" href="/${contributor['id']}/">${condensed}</a></li>
        % else:
            <span rel="${'tooltip' if is_condensed else ''}" title="${contributor['fullname']}">${condensed}</span></li>

        %endif
% endfor


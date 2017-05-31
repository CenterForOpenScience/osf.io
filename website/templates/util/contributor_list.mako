<%def name="render_contributor_dict(contributor)">
  % if contributor['user_is_claimed']:
      <a class="overflow"
              rel="tooltip"
              href="${contributor['user_profile_url']}"
              data-original-title="${contributor['user_fullname']}"
              >${contributor['user_display_name']}</a><span>${ contributor['separator'] | n }</span>
  % else:
      <span class="overflow">${contributor['user_display_name']}</span><span>${ contributor['separator'] | n }</span>
  % endif
</%def>

<%def name="render_contributors(contributors, others_count, node_url)">
  % for i, contributor in enumerate(contributors):
    ${render_contributor_dict(contributor) if isinstance(contributor, dict) else render_user_obj(contributor)}
  % endfor
  % if others_count:
      <a href="${node_url}">${others_count} more</a>
  % endif
</%def>

<%def name="render_contributors_full(contributors)">
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
</%def>

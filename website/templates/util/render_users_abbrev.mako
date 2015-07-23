<div class="project-authors">
  ${render_contributors(contributors, others_count)}
</div>

<%def name="render_user(contributor)">
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

<%def name="render_contributors(contributors, others_count)">
  % for i, contributor in enumerate(contributors):
      ${render_user(contributor)}
  % endfor
  % if others_count:
      <a href="${node_url}">${others_count} more</a>
  % endif
</%def>


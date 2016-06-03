<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Forum</%def>

<div class="page-header visible-xs">
  <h2 class="text-300">Forum</h2>
</div>

<iframe style="overflow-y:scroll;border:none;" width="100%" height="600" src="${ forum_url }"></iframe>

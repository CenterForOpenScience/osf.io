<%inherit file="project.view.mako" />
<form method="post" action="${node_to_use.url()}/remove">
  <button type="submit" class="btn primary">Delete this component and all non-project components</button>
 </form>

<%namespace file="_render_keys.mako" import="render_keys" />
${render_keys(node_to_use, node_to_use.url())}
<%inherit file="project.view.mako" />

<%namespace file="_render_key_history.mako" import="render_key_history" />
${render_key_history(api_key, route)}
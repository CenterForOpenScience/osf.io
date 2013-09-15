<%inherit file="membersOuter.mako" />

<h2>Profile</h2>

<%namespace file="_render_keys.mako" import="render_keys" />
${render_keys(user, '/settings')}

<%inherit file="project/project_base.mako"/>

<h1>Dryad Browser</h1>
<p>Viewing ${start} through ${end} of ${total}<p>
% if not end ==total:
<a href="">Next</a>
% endif
% if not start == 0:
<a href="">previous</a>
% endif
${content}

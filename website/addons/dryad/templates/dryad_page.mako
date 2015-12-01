<%inherit file="project/project_base.mako"/>

<h1>Dryad Browser</h1>
<p>Viewing ${start} through ${end} of ${total}<p>
% if not end ==total:
<a href="${next_dryad}">Next</a>
% else:
<span>Next</span>
% endif
% if not start == 0:
<a href="${previous_dryad}">Previous</a>
% else:
<span>Previous</span>
% endif
${content}


% if not end ==total:
<a href="${next_dryad}">Next</a>
% else:
<span>Next</span>
% endif
|
% if not start == 0:
<a href="${previous_dryad}">Previous</a>
% else:
<span>Previous</span>
% endif

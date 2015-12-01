<%inherit file="project/project_base.mako"/>

<h1>Dryad Browser</h1>
<p>Viewing ${start} through ${end} of ${total}<p>

% if not start == 0:
<a href="${previous_dryad}">Previous</a>
% else:
<span>Previous</span>
% endif
|
% if not end ==total:
<a href="${next_dryad}">Next</a>
% else:
<span>Next</span>
% endif
<form action="{href: urls().search}">
Search:
<input type="text" name="query" value="doi:10.5061/dryad.XXXX">
<input type="submit" value="Search">
</form>

${content}

% if not start == 0:
<a href="${previous_dryad}">Previous</a>
% else:
<span>Previous</span>
% endif
|
% if not end ==total:
<a href="${next_dryad}">Next</a>
% else:
<span>Next</span>
% endif

<%inherit file="project/project_base.mako"/>

<h1>Dryad Browser</h1>
<p>Viewing ${start} through ${end} of ${total}<p>

<small class=" pull-right">
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
</small>
<small class="pull-left">
	<form action="${search_dryad_url}">
		Search:
		<input type="text" name="query" value="Enter Text Here">
		<input type="submit" value="Search">
	</form>
</small>
<br/>
<hr/>
<small>
	${content}
</small>
<br/>
<hr/>
<small class=" pull-right">
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
</small>


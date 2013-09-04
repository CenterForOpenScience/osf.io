%for v in versions:
	<p>
		%if node:
			<a href="/project/${project._primary_key}/node/${node._primary_key}/wiki/${pageName}/compare/${v.version}">
		%else:
			<a href="/project/${project._primary_key}/wiki/${pageName}/compare/${v.version}">
		%endif
			Version ${v.version} edited by ${v.user.fullname} on ${v.date}
		</a>
	</p>
%endfor
% for version in versions:
	<p id="version">
        <a href="${node['url']}wiki/${pageName}/compare/${version['version']}">
        Version ${version['version']} edited by ${version['user_fullname']} on ${version['date']}
		</a>
	</p>

% endfor

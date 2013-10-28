% for version in versions:
	<p>
        <a href="${node_url}wiki/${pageName}/compare/${version['version']}">
        Version ${version['version']} edited by ${version['user_fullname']} on ${version['date']}
		</a>
	</p>
% endfor
% for version in versions:
	<p style="text-align: right">
        <a href="${node['url']}wiki/${pageName}/compare/${version['version']}">
        Version ${version['version']} edited by ${version['user_fullname']} on ${version['date']}
		</a>
	</p>
% endfor

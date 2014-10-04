<%! import urllib %>

% for version in versions:
	<p style="text-align: right">
        <a href="${node['url']}wiki/${urllib.quote(pageName.encode('utf-8'))}/compare/${version['version']}">
            Version ${version['version']} edited
            % if not node['anonymous']:
                by ${version['user_fullname']}
            % endif
            on ${version['date']}
        </a>
	</p>
% endfor

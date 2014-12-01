<%page expression_filter="h"/>

% for version in versions:
	<p style="text-align: right">
        <a href="${version['compare_web_url']}">
            Version ${version['version']} edited
            % if not node['anonymous']:
                by ${version['user_fullname']}
            % endif
            on <span id="version-${version['version']}"></span>

            <script type="application/javascript">
                var versionDate = new $.osf.FormattableDate("${version['date']}");
                $("#version-${version['version']}").text(versionDate.local);
            </script>
        </a>
	</p>
% endfor

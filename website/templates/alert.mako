<script type="application/javascript">
    function capitaliseFirstLetter(string)
        {
            return string.charAt(0).toUpperCase() + string.slice(1);
        }
</script>
<div id="alert-container">
% for message, css_class, dismissible in status:
        % if dismissible:
                <script type="application/javascript">
                    var title = capitaliseFirstLetter('${css_class | trim}')+':';
                    var message = '${message | trim}';
                    var type = '${css_class | trim}';
                    $.osf.growl(title, message, type);
                </script>
        % else:
            <div class='alert alert-block alert-${css_class} fade in'>
            	<p>${message}</p>
            </div>
        % endif
% endfor
</div>

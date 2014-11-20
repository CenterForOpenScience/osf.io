<div id="alert-container">
% for message, css_class, dismissible in status:
    <div class='alert alert-block alert-${css_class} fade in'>
        % if dismissible:
            <a class='close' data-dismiss='alert' href='#'>&times;</a>
        % endif
    <p>${message}</p></div>
% endfor
</div>

<div id="alert-container">
% for message, css_class in status:
    <div class='alert alert-block alert-${css_class} fade in'><a class='close' data-dismiss='alert' href='#'>&times;</a><p>${message}</p></div>
% endfor
</div>

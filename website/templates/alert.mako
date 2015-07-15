<%page args="extra_css=''" />

<div id="alert-container" class="m-t-md">
% for message, css_class, dismissible, trust in status:
      <div class='alert alert-block alert-${css_class} fade in ${extra_css}'>
        % if dismissible:
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
        % endif

        % if trust:
          <p>${message | n}</p>
        % else:
          <p>${message}</p>
        % endif
      </div>
% endfor
</div>

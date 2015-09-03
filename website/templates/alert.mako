<%page args="extra_css=''" />

<div id="alert-container" class="m-t-md">
% for message, jumbotron, css_class, dismissible, trust in status:
      <div class='alert alert-block alert-${css_class} fade in ${extra_css}'>
        % if dismissible:
        <button type="button" class="close${' m-r-sm' if jumbotron else ''}" data-dismiss="alert" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
        % endif

        %if jumbotron:
        <div class="jumbotron">
        %endif
        % if trust:
          <p>${message | n}</p>
        % else:
          <p>${message}</p>
        % endif
        %if jumbotron:
        </div>
        %endif
      </div>
% endfor
</div>

<div id="alert-container">
% for message, css_class, dismissible, safe in status:
      <div class='alert alert-block alert-${css_class} fade in'>
        % if dismissible:
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
        % endif

        % if safe:
          <p>${message | n}</p>
        % else:
          <p>${message}</p>
        % endif
      </div>
% endfor
</div>

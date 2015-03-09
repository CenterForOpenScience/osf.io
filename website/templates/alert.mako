<div id="alert-container">
% for message, css_class, dismissible in status:
      <div class='alert alert-block alert-${css_class} fade in'>
        % if dismissible:
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
        % endif
        <p>${message}</p>
      </div>
% endfor
</div>

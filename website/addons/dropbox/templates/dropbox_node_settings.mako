<%inherit file="project/addon/node_settings.mako" />

<script src="/static/vendor/bower_components/typeahead.js/dist/typeahead.jquery.js"></script>
<script src="/static/vendor/bower_components/typeahead.js/dist/bloodhound.min.js"></script>
<link rel="stylesheet" href="/addons/static/dropbox/node_settings.css">

<script>
$(document).ready(function() {

//Thanks to http://stackoverflow.com/questions/3463954/jquery-click-through-class-cycle
$.fn.cycleClasses = function() {
  var classes, currentClass, nextClass, _this = this;
  classes = Array.prototype.slice.call(arguments);

  currentClass = $.grep(classes, function(klass) {
    _this.hasClass(klass);
  }).pop();

  nextClass = classes[classes.indexOf(currentClass) + 1] || classes[0];

  this.removeClass(currentClass);
  return this.addClass(nextClass);
};

    stuff = [
        {text:'Root', value:'/'},
        {text:'TestFolder', value:'/TestFolder/'}
    ];

    var bloodhound = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.obj.nonword('text'),
        queryTokenizer: Bloodhound.tokenizers.nonword,
        local: stuff
    });

    bloodhound.initialize();



    $('#dropboxFolderSelect').typeahead({
      highlight: true,
      minLength: 0
    },
    {
        name: 'projects',
        displayKey: 'text',
        source: bloodhound.ttAdapter()
    });
    $('#dropboxFolderSelect').on('change paste keyup',function() {
        if($(this).val() && $(this).val().trim())
            $('#figshareSubmit').prop('disabled', false);
        else
            $('#figshareSubmit').prop('disabled', true);
    });
});
</script>

       <div class="row">
            <div class="col-md-12">
                <div class="input-group">
                    <input class="form-control" id="dropboxFolderSelect" type="text" placeholder="Choose a folder">
                    <span class="input-group-btn">
                        <button id="figshareSubmit" type="button" class="btn btn-success" disabled="disabled">Submit</button>
                    </span>
                </div>
            </div>
    </div>

<%def name="submit_btn()">
</%def>


<%def name="title()">
    <h4>
        ${addon_full_name}
        % if node_has_auth:
        <small> Authorized by <a href="${owner_url}">${owner}</a></small>
            %if user_has_auth:
                <small  class="pull-right" >
                    <a id="dropboxDelKey" class="text-danger" style="cursor: pointer">Deauthorize</a>
                </small>
            %endif
        %endif
    </h4>
</%def>

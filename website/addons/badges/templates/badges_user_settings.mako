<%inherit file="project/addon/user_settings.mako" />
%if len(badges) < 1:
You have not created any Badges.
%endif
  <div style="max-height:200px; overflow-y: auto; overflow-x: hidden;">
    <ul class="media-list" id="badgeList">
        %for badge in badges:
        <li class="media">
          <a class="pull-left">
            <img class="media-object" src="${badge['image']}" width="64px" height="64px">
          </a>
          <div class="media-body">
            <h4 class="media-heading">${badge['name']}<small> ${badge['description']} </small></h4>

            ${badge['criteria']}
          </div>
        </li>
        %endfor
    </ul>
  </div>

  <br />

  <button class="btn btn-primary" id="newBadge" type="button">
    New Badge
  </button>

<script type="text/javascript" src="/static/vendor/dropzone/dropzone.js"></script>
<script type="text/javascript">
//TODO Make bootbox into a form? [with submit]
//TODO Image uploading
    $(document).ready(function() {
        $('#newBadge').click(function(){
            bootbox.dialog({
              message: '<form id="badgeForm">' +
              '<input type="text" class="form-control" name="badgeName" placeholder="Badge Name"><br />' +
              '<input type="text" class="form-control" name="description" placeholder="Description"><br />' +
              '<input type="url" class="form-control" name="imageurl" placeholder="Image URL"><br />' +
              '<textarea class="form-control" name="criteria" placeholder="Criteria" />' +
              '</form>',
              title: 'Create a new badge',
              buttons: {
                submit: {
                  label: "Submit",
                  className: "btn-success",
                  callback: function() {
                    var data = AddonHelper.formToObj('#badgeForm');
                    if(notEmpty(data)) {
                      $.ajax({
                        url: '/api/v1/badges/new/',
                        type: 'POST',
                        dataType: 'json',
                        contentType: 'application/json',
                        data: JSON.stringify(data),
                        success: function(response) {
                          %if len(badges) > 0:
                            $("#badgeList").append(jsonToList(data, response.badgeid));
                          %else:
                            document.location.reload(true);
                          %endif
                        },
                        error: function(xhr) {
                          alert('Failed: ' + xhr.statusText);
                        }
                      });
                    }
                  else {
                  alert('All fields must be filled out.')
                  return false;
                }
                  }
                },
                // upload: {
                //   label: "Upload Image",
                //   className: "btn-primary",
                //   callback: function() {
                //     //Maybe another time
                //   }
                // },
                cancel: {
                  label: "Cancel",
                  className: "btn-default"
                }
              }
            });
        });
    });

  var notEmpty = function(list) {
    for(var key in list) {
      if(list[key].trim() === "")
        return false;
    }
    return true;
  };

//todo fetch url from server
  var jsonToList = function(badge, id) {
      // TODO: Rewrite this substantially before this feature is re-activated
    return '<li class="media">' +
          '<a class="pull-left" href="/' + id + '/">' +
            '<img class="media-object" src="' + badge['imageurl'] + '" width="64px" height="64px"> </a>' +
                  '<div class="media-body">' +
                    '<h4 class="media-heading">' + badge['badgeName'] + '<small> ' + badge['description'] + '</small></h4>' +
        badge['criteria'] +
      '</div>' +
    '</li>'
  };

</script>

<%def name="submit_btn()">
</%def>
<%def name="on_submit()">
</%def>

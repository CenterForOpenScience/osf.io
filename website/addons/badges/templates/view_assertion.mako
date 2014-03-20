<link rel="stylesheet" href="/static/vendor/bower_components/bootstrap/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="/static/vendor/bower_components/bootstrap/dist/css/bootstrap-theme.min.css">
<br />
<div class="media well">
  <a class="pull-left" href="/badge/assertions/${uid}/json/">
    <img class="media-object" src="${image}" width="150px" height="150px">
  </a>
  <div class="media-body">
    <h3 class="media-heading">${name}
        <small> ${description} </small>
        <small class="pull-right">Endorsed by <a href="${issuer}">${issuer_name}</a></small>
        </h3>
    ${criteria} <br />
    <h4>Awarded to <a href="/${recipient['identity']}/">{project_name}</a><small> on ${issued_on}</small></h4>
  </div>
</div>
<!-- TODO Bake image here -->

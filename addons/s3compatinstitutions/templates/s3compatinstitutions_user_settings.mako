<!-- Authorization -->
<div class="addon-oauth"
     data-addon-short-name="${ addon_short_name }"
     data-addon-name="${ addon_full_name }">
    <!-- This is not "addon-title" to ignore "Import Account from Admin" -->
    <h4 class="addon-title-s3compatinstitutions">
      <img class="addon-icon" src="${addon_icon_url}">
      <span data-bind="text:properName"></span>
    </h4>
    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>
</div>

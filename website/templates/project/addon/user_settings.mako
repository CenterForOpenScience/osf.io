<%inherit file="settings.mako" />

        ${self.body()}

        ${self.submit_btn()}

<%def name="submit_btn()">
    ##<button class="btn btn-success addon-settings-submit">
       ## Submit
    ##</button>
</%def>
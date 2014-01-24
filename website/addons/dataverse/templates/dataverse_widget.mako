<%inherit file="project/addon/widget.mako"/>

<div>
    Showing URL <a href="${dataverse_url}">${dataverse_url}</a>
</div>

<iframe
        src="${dataverse_url}"
        frameborder="0"
    ></iframe>

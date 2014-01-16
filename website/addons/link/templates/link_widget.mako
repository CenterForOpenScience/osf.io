<%inherit file="project/addon/widget.mako"/>

<div>
    Showing URL <a href="${link_url}">${link_url}</a>
</div>

<iframe
        src="${link_url}"
        frameborder="0"
    ></iframe>

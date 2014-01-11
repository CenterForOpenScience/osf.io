<%inherit file="project/addon/settings.mako" />

<div class="form-group">
    <label for="zoteroId">Zotero User/Group ID</label>
    <input class="form-control" id="zoteroId" name="zotero_id" value="${zotero_id}" ${'disabled' if disabled else ''} />
</div>

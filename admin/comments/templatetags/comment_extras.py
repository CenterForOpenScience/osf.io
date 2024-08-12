from django import template

from admin.base.utils import reverse_qs

register = template.Library()


@register.simple_tag
def reverse_comment_detail(comment, *args, **kwargs):
    return reverse_qs(
        "comments:comment-detail",
        kwargs={"comment_id": comment.id},
        query_kwargs=kwargs,
    )


@register.simple_tag
def reverse_comment_list(*args, **kwargs):
    return reverse_qs("comments:comments", query_kwargs=kwargs)


@register.simple_tag
def reverse_comment_user(user, *args, **kwargs):
    return reverse_qs(
        "comments:user-comment",
        kwargs={"user_guid": user._id},
        query_kwargs=kwargs,
    )

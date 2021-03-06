from django import template
from django.conf import settings

register = template.Library()


def show_profile(context, user):
    return {"user": user,
            "request": context["request"],
            "STATIC_URL": settings.STATIC_URL}
register.inclusion_tag("profiles/profile_item.html",
                       takes_context=True)(show_profile)


def clear_search_url(request):
    getvars = request.GET.copy()
    if 'search' in getvars:
        del getvars['search']
    if len(getvars.keys()) > 0:
        return "%s?%s" % (request.path, getvars.urlencode())
    else:
        return request.path
register.simple_tag(clear_search_url)

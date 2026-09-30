from django.conf import settings


def site(request):
    context = {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_TAGLINE': settings.SITE_TAGLINE,
        'balance': 0,
    }
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        profile = getattr(user, 'profile', None)
        context['balance'] = profile.balance if profile else 0
    return context
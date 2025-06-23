from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.exceptions import MultipleObjectsReturned
from django.contrib.sites.shortcuts import get_current_site  # ✅ Add this import

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_app(self, request, provider, client_id=None, scope=None):
        from allauth.socialaccount.models import SocialApp

        apps = SocialApp.objects.filter(provider=provider)

        if client_id:
            apps = apps.filter(client_id=client_id)

        current_site = get_current_site(request)  # ✅ Use this instead of request.site
        apps = apps.filter(sites=current_site)

        if not apps.exists():
            raise Exception(f"No SocialApp configured for provider {provider} and site {current_site}")
        if apps.count() > 1:
            raise MultipleObjectsReturned(f"Multiple SocialApps found for provider {provider} and site {current_site}. Apps: {apps.values_list('id', flat=True)}")

        return apps.first()


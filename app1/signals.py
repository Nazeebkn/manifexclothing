from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from .models import Referral
from wallet.models import Wallet

"""
Create a referral code and wallet for users who sign up.
"""
@receiver(user_signed_up)
def create_referral_code_for_user(request, user, **kwargs):
    Referral.objects.create(user=user)
    Wallet.objects.create(user=user)
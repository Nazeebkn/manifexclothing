
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string

class OTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return timezone.now() <= self.expires_at
    



"""
REFERRAL OPTION
"""
class Referral(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referral')
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')

    def save(self, *args, **kwargs):
        if not self.referral_code:
            # Generate a structured referral code
            date_part = timezone.now().strftime("%Y%m%d")  # Current date in YYYYMMDD format
            user_part = self.user.username[:3].upper()  # First 3 characters of the username
            random_part = get_random_string(3).upper()  # Random 3-character string
            self.referral_code = f"REF-{date_part}-{user_part}-{random_part}"
        super().save(*args, **kwargs)

    def _str_(self):
        return f"{self.user.username} - {self.referral_code}"

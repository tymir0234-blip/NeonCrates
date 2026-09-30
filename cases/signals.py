from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile

START_BALANCE = 10000


@receiver(post_save, sender='auth.User')
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(
            user=instance, defaults={'balance': START_BALANCE}
        )
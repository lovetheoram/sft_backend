# society/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Member,Income,Notification

@receiver(post_save, sender=User)
def create_member_for_resident(sender, instance, created, **kwargs):
    if created and instance.flat is not None and not hasattr(instance, 'member'):
        Member.objects.create(user=instance)


@receiver(post_save, sender=Income)
def notify_admin_on_income(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.member.user,  # linked to the resident
            income=instance,
            message=f"{instance.member.user.get_full_name()} submitted ₹{instance.amount} for verification.",
            seen=False
        )


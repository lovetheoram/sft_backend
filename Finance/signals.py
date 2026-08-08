from datetime import date
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import User, Member, Income, Expense, SpecialCharge, Notification


@receiver(post_save, sender=User)
def create_member_for_resident(sender, instance, created, **kwargs):
    if created and instance.flat is not None and not hasattr(instance, 'member'):
        Member.objects.create(user=instance)


# Income notifications on creation removed as admins audit income directly in Income Audit panel


def _invalidate_financial_summary_cache(building_id, event_date=None):
    """
    Automatically invalidates financial summary cache keys whenever 
    financial records (Income, Expense, SpecialCharge) are created, updated, or deleted.
    """
    if not building_id:
        return
    try:
        if event_date:
            year = getattr(event_date, 'year', None) or date.today().year
            for y in range(year - 2, year + 3):
                cache.delete(f"fin_summary_{building_id}_{y}")
        else:
            current_year = date.today().year
            for y in range(current_year - 5, current_year + 3):
                cache.delete(f"fin_summary_{building_id}_{y}")
    except Exception:
        pass


@receiver(post_save, sender=Income)
@receiver(post_delete, sender=Income)
def invalidate_summary_on_income_change(sender, instance, **kwargs):
    building_id = getattr(instance, 'building_id', None)
    _invalidate_financial_summary_cache(building_id, getattr(instance, 'date', None))


@receiver(post_save, sender=Expense)
@receiver(post_delete, sender=Expense)
def invalidate_summary_on_expense_change(sender, instance, **kwargs):
    building_id = getattr(instance, 'building_id', None)
    _invalidate_financial_summary_cache(building_id, getattr(instance, 'date', None))


@receiver(post_save, sender=SpecialCharge)
@receiver(post_delete, sender=SpecialCharge)
def invalidate_summary_on_special_charge_change(sender, instance, **kwargs):
    building_id = getattr(instance, 'building_id', None)
    _invalidate_financial_summary_cache(building_id, None)



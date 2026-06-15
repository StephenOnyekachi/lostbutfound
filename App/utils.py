
from django.utils import timezone


def check_subscription(org):
    today = timezone.now().date()

    # 1. If user has active paid subscription
    if org.subscription_end:
        if org.subscription_end >= today:
            org.status = "active"
            org.is_trial = False
            org.save(update_fields=["status", "is_trial"])
            return
        else:
            org.subscription_end = None

    # 2. Trial period check
    if org.trial_end:
        if org.trial_end >= today:
            org.status = "active"
            org.is_trial = True
            org.save(update_fields=["status", "is_trial"])
            return

    # 3. Expired everything → block org
    org.status = "inactive"
    org.save(update_fields=["status"])


    

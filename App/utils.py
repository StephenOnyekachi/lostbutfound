

from django.utils import timezone

def check_subscription(org):
    """
    Returns True if org is still valid (trial or paid), False if expired
    """

    today = timezone.now().date()

    # still in trial
    if org.is_trial and org.trial_end:
        return org.trial_end >= today

    # paid subscription check
    if org.subscription_end:
        return org.subscription_end >= today

    # if no subscription set → treat as expired
    return False




from django.shortcuts import redirect
from django.urls import resolve
from .models import Profile
from .utils import check_subscription


class OrgStatusMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated and not request.user.is_superuser:

            profile = Profile.objects.filter(
                user=request.user
            ).select_related("org").first()

            if profile and profile.org:

                current_url = resolve(request.path_info).url_name

                allowed_urls = [
                    "payments",
                    "renewpayment",
                    "logout",
                ]

                org = profile.org

                # 🔥 NEW SUBSCRIPTION CHECK
                is_valid = check_subscription(org)

                if (not is_valid and current_url not in allowed_urls):
                    return redirect("payments")

                # EXISTING STATUS CHECK
                if (
                    org.status in ["inactive", "suspended"]
                    and current_url not in allowed_urls
                ):
                    return redirect("payments")

        return self.get_response(request)


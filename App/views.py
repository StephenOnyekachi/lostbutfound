

# from django.contrib.auth.models import User
from django.http import HttpResponse,JsonResponse
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.db.models import Q, F, Sum
import random, time, datetime, requests
from decimal import Decimal, InvalidOperation
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from . models import *
import re
from django.conf import settings
from django.core.cache import cache

# for emails
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from celery import shared_task

# Create your views here.

# deffine speruser function
def is_superuser(user):
    return user.is_superuser


# redirect user if not superuser
def CheckUser(view_func):
    return user_passes_test(
        is_superuser,
        login_url='dashboard',
        redirect_field_name=None
    )(view_func)


# celery task for sending email asynchronously
@shared_task(bind=True, max_retries=3)
def SendEmailTask(self, subject, html, email):
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Sending email to {email}")

        from django.core.mail import EmailMultiAlternatives

        msg = EmailMultiAlternatives(
            subject=subject,
            body="This email requires HTML support.",
            to=[email]
        )
        msg.attach_alternative(html, "text/html")
        msg.send()

    except Exception as exc:
        logger.error(f"Failed to send email to {email}: {exc}")
        raise self.retry(exc=exc, countdown=60)


# # for sending function with redis
# def SendMail(user, template_name, email_subject, extra_context=None):
#     name = user.get_full_name() or user.username
#     recipient_email = user.email

#     context = {
#         'name': name,
#         'email': recipient_email,
#     }

#     if extra_context:
#         context.update(extra_context)

#     html_content = render_to_string(template_name, context)

#     SendEmailTask.delay(email_subject, html_content, recipient_email)


# for sending function
def SendMail(user, template_name, email_subject, extra_context=None):
    name = user.get_full_name() or user.username
    recipient_email = user.email

    context = {
        'name': name,
        'email': recipient_email,
    }

    if extra_context:
        context.update(extra_context)

    html_content = render_to_string(template_name, context)

    from django.core.mail import EmailMultiAlternatives

    msg = EmailMultiAlternatives(
        subject=email_subject,
        body=html_content,
        to=[recipient_email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


# sending otp code to the user email
def OTP(user):
    # for generation login otp code
    # code = str(random.randint(100000, 999)).zfill(6)
    code = ''.join(random.choices('0123456789', k=6))
    # OTPCode.objects.create(
    #     otp=code,
    #     receiver=user
    # )
    print('login code is', code)
    subject = 'Your OTP Code'
    extra_context = {
        'code':code
    }

    SendMail(user, 'extends/login-otp-mail.html', subject, extra_context)


# function to get org users with caching
def get_org_users(org_id):
    key = f"org_users_{org_id}"

    users = cache.get(key)
    if not users:
        users = list(Profile.objects.filter(org_id=org_id))
        cache.set(key, users, 300)  # 5 min

    return users


# logout function
def UserLogout(request):
    user = request.user

    # logout user once
    logout(request)
    messages.success(
        request,
        "You have been logged out successfully"
    )

    # admin logout
    if user.is_superuser:
        return redirect("login")

    # if user came from an organization subdomain
    subdomain = GetSubdomain(request)
    if subdomain:
        return redirect("memberlogin")

    return redirect("login")


# logout user out after 24 hours
def AutoLogout(request, timeout_day = 1):
    # timeout_minues = timeout_hour * 60 # for 12 hour
    timeout_minues = timeout_day * 24 * 60 # for 24 hour
    now = datetime.datetime.now()
    try:
        last_activity = request.session['last_activity']
        last_activity = datetime.datetime.fromisoformat(last_activity)
        if(now - last_activity).total_seconds() / 60 > timeout_minues:
            logout(request)
    except KeyError:
        pass
    # request.session['last_active']=datetime.datetime.now()
    request.session['last_activity'] = now.isoformat()


# login function
def UserLogin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:

            login(request, user)

            if user.is_superuser:
                messages.success(request, f"Welcome back {user.username}")
                return redirect('adminpage')

            messages.success(request, f"Welcome back {user.username}")
            return redirect('dashboard')
        
        messages.error(request, 'Incorrect username or password, please try again')
        return redirect('login')
    
    context={}

    return render(request,"login.html",context)
    # return HttpResponse('welcome to django')


# user signup
def OrgSignup(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")

        org_name = request.POST.get("org_name")
        subdomain = request.POST.get("sub_name", "").strip().lower()
        logo = request.FILES.get("logo")

        phone = request.POST.get("phone")
        gender = request.POST.get("gender")

        # verifing password
        if password:

            # validating org name
            if not org_name:
                messages.error(request, "Organization name is required")
                return redirect("signup")
            
            # checking if email already exist
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email have been used, try another email')
                return redirect("signup")
            
            # checking if email or username already exist
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists")
                return redirect("signup")
            
            # checking if username already exist
            if not re.match(r'^[a-z0-9-]+$', subdomain):
                messages.error(
                    request,
                    "Subdomain can only contain letters, numbers and hyphens"
                )
                return redirect("signup")
            
            # checking if subdomain already exist
            if Org.objects.filter(subdomain=subdomain).exists():
                messages.error(request, "Subdomain already taken")
                return redirect("signup")
                
            # to prevent error occurance while creating account
            with transaction.atomic():
                
                # creating user
                profile = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                )
                
                org = Org.objects.create(
                    orgname=org_name,
                    subdomain=subdomain,
                    logo=logo,
                    owner=profile,
                    owner_number=phone
                )

                # creating profile for user
                Profile.objects.create(
                    user=profile,
                    gender=gender,
                    phone_number=phone,
                    org=org,
                    role='admin'
                    # info=password1,
                )

            # calling sending mail functionn here after creating account
            subject = 'Welcome to Lost But Found'
            extra_context={
                'org':org
            }
            SendMail(profile, 'extends/newOrgMail.html', subject, extra_context)

            messages.success(request, f'you successfully created a new account with lost but found "{org_name}"')
            return redirect("login")
        
        messages.error(request, f'you have to set a password to create an account')
        return redirect("signup")
    
    return render(request,"signup.html")


# function to get subdomain from request
def GetSubdomain(request):
    host = request.get_host().split(":")[0].lower()

    # remove www
    if host.startswith("www."):
        host = host.replace("www.", "")

    parts = host.split(".")

    # localhost case
    if host in ["localhost", "127.0.0.1"]:
        return request.GET.get("sub_name") or request.POST.get("sub_name")

    # production / staging
    if len(parts) < 3:
        return None  # no subdomain (example.com)

    return parts[0]


# for user signup with org link
def UserSignup(request):

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")

        phone = request.POST.get("phone")
        gender = request.POST.get("gender")
        
        # Determine subdomain based on the host
        subdomain = GetSubdomain(request)

        # verifing password
        if not password:
            messages.error(request, "You have to set a password to create an account")
            return redirect("register")

        # verifying subdomain and org
        org = Org.objects.filter(subdomain=subdomain).first()

        # verify org
        if not org:
            messages.error(request, "Invalid organization link")
            return redirect("register")

        # verify status
        if org.status != "active":
            messages.error(request, "Organization is inactive")
            return redirect("register")

        # verifying email
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already used")
            return redirect("register")

        # verifying username
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("register")

        # to prevent error occurance while creating account
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            Profile.objects.create(
                user=user,
                org=org,
                role="member",
                gender=gender,
                phone_number=phone,
            )

        # calling sending mail functionn here after creating account
        subject = ('Welcome to', org.orgname)
        extra_context={
            'org':org
        }
        SendMail(user, 'extends/newUserMail.html.html', subject, extra_context)

        messages.success(request, "Account created successfully")
        return redirect("memberlogin")
    
    # Detect organization from subdomain
    signuporg = None
    subdomain = GetSubdomain(request)
    if subdomain:
        signuporg = get_object_or_404(Org, subdomain=subdomain)

    context = {
        "org": signuporg
    }

    return render(request, "users/signup.html", context)


# for member login
def MemberLogin(request):

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        # verifying user credentials
        if not user:
            messages.error(request, "Invalid username or password")
            return redirect("memberlogin")

        # Prevent superusers from using member login
        if user.is_superuser:
            messages.error(request, "Use admin login instead")
            return redirect("memberlogin")

        # verifying user profile and organization
        profile = Profile.objects.filter(user=user).first()
        if not profile:
            messages.error(request, "Profile not found")
            return redirect("memberlogin")

        # Detect organization from subdomain
        subdomain = GetSubdomain(request)

        # Verify member belongs to current organization
        if profile.org.subdomain != subdomain:
            messages.error(
                request,
                "You do not belong to this organization"
            )
            return redirect("memberlogin")

        # Optional: ensure org is active
        if profile.org.status != "active":
            messages.error(
                request,
                "Organization is inactive"
            )
            return redirect("memberlogin")

        # log in the user
        login(request, user)
        messages.success(request, f"Welcome back {user.username}")
        return redirect("dashboard")
    
    # Detect organization from subdomain
    subdomain = GetSubdomain(request)
    if subdomain:
        signuporg = get_object_or_404(Org, subdomain=subdomain)
        context = {
            'org':signuporg,
        }
    else:
        context = {}

    return render(request, "users/login.html", context)


# for inex or landing page
def Index(request):

    # for getting all plans
    # plan1 = Plan.objects.get(id=1)
    # plan2 = Plan.objects.get(id=2)
    # plan3 = Plan.objects.get(id=3)
    plan1, created = Plan.objects.get_or_create(id=1)
    plan2, created = Plan.objects.get_or_create(id=2)
    plan3, created = Plan.objects.get_or_create(id=3)

    context = {
        'plan1':plan1,
        'plan2':plan2,
        'plan3':plan3,
    }
    return render(request, 'index.html', context)
    # return HttpResponse('welcome to django')


# for org dashboard
@login_required(login_url='login')
def Dashboard(request):

    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # get all user in the same org
    org = profile.org
    users = Profile.objects.filter(org=org)

    # get all found items
    foundItems = Item.objects.filter(org=org, status='found')

    # get all claimed items
    claimedItems = Item.objects.filter(org=org, status='claimed')

    # get all claimed items
    claimmers = Claim.objects.filter(org=org)

    # get all items
    allItems = Item.objects.filter(org=org)

    context = {
        'profile':profile,
        'users':users,
        'org':org,
        'foundItems':foundItems,
        'claimedItems':claimedItems,
        'claimmers':claimmers,
        'allItems':allItems,
    }

    return render(request, 'users/dashboard.html', context)


# for org profile
@login_required(login_url='login')
def OrgProfile(request):
    
    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # get all user in the same org
    org = profile.org
    if not org:
        return redirect('dashboard')
    users = Profile.objects.filter(org=org)

    if request.method == 'POST':
        name = request.POST.get("name")
        logo = request.FILES.get("logo")

        if name:
            org.orgname = name
        if logo:
            org.logo = logo
        org.save()
        return redirect('orgprofile')

    context = {
        'profile':profile,
        'users':users,
        'org':org,
    }
    return render(request, 'users/profile.html', context)


# for deletting org
@login_required(login_url='login')
def DeleteOrg(request, pk):
    
    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # verify if user role is admin
    if profile.role != 'admin':
        return redirect('dashboard')

    # check if user have org
    if not profile.org:
        return redirect('dashboard')

    # get org id
    org = get_object_or_404(Org, id=pk)
    if not profile.org or org.id != profile.org.id:
        return redirect('dashboard')
    
    # delete org
    org.delete()
    return redirect('index')


# for org payment renew
@login_required(login_url='login')
def Payments(request):
    
    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # get all org payment
    org = profile.org
    payment = Payment.objects.filter(org=org)

    context = {
        'profile':profile,
        'payment':payment,
    }
    return render(request, 'users/payments.html', context)


# for org renew plans
@login_required(login_url='login')
def RenewPayment(request):
    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # for getting all plans
    plan1 = Plan.objects.get(id=1)
    plan2 = Plan.objects.get(id=2)
    plan3 = Plan.objects.get(id=3)

    context = {
        'profile':profile,
        'plan1':plan1,
        'plan2':plan2,
        'plan3':plan3,
    }
    return render(request, 'users/renewPayment.html', context)


# for org users
@login_required(login_url='login')
def OrgUsers(request):
    
    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # get all user in the same org
    org = profile.org
    users = Profile.objects.filter(org=org)
    # users = Profile.objects.filter(org=org, role='member', role='staff')

    context = {
        'profile':profile,
        'users':users,
        'org':org,
    }
    return render(request, 'users/users.html', context)


# for org users
@login_required(login_url='login')
def DeleteUser(request, pk):

    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # verify if user role is admin
    if profile.role != 'admin':
        return redirect('orgusers')

    target_user = get_object_or_404(User, id=pk)
    target_profile = get_object_or_404(Profile, user=target_user)

    if target_profile.org != profile.org:
        return redirect('dashboard')

    target_user.delete()

    return redirect('orgusers')


# for found items
@login_required(login_url='login')
def FoundItems(request):
    
    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # get item org
    org = profile.org

    # get all found items
    items = Item.objects.filter(status='found', org=org)

    context = {
        'profile':profile,
        'items':items,
    }
    return render(request, 'users/foundItems.html', context)


# for claimed items
@login_required(login_url='login')
def ClaimedItems(request):
    
    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # get item org
    org = profile.org

    # get all found items
    items = Item.objects.filter(status='claimed', org=org)

    context = {
        'profile':profile,
        'items':items,
    }
    return render(request, 'users/claimedItems.html', context)


# for delete items
@login_required(login_url='login')
def DeleteItem(request, pk):
    
    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # get item org
    org = profile.org

    # get item id
    item = get_object_or_404(Item, id=pk, org=profile.org)
    if item.org_id != profile.org.id:
        return redirect('dashboard')
    
    # delete user
    item.delete()

    print('item id:', item.id)

    return redirect('dashboard')


# for adding items
@login_required(login_url='login')
def AddItems(request):

    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # get item org
    org = profile.org

    # importing choices
    category = Item.CATEGORY_CHOICES
    status = Item.STATUS_CHOICES

    # varifing org
    if not org:
        messages.error(request, "Organization not found")
        return redirect('dashboard')

    if request.method == 'POST':
        name = request.POST.get("name")
        picture = request.FILES.get("image")
        category = request.POST.get("category")
        status = request.POST.get("status")
        location = request.POST.get("location")
        description = request.POST.get("description")

        item = Item.objects.create(
            name=name,
            picture=picture,
            category=category,
            status=status,
            location_found=location,
            description=description,
            org_id=org.id,
            posted_by_id=profile.id
        )

        return redirect('dashboard')

    context = {
        'profile':profile,
        'category':category,
        'status':status
    }
    return render(request, 'users/addItem.html', context)


# for claiming items
@login_required(login_url='login')
def Claimmers(request):

    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # get claimmer org
    org = profile.org

    # get all claimed items
    claimmers = Claim.objects.filter(org=org)
    
    # importing choices
    status = Claim.STATUS_CHOICES

    if request.method == 'POST':
        status = request.POST.get("status")
        id = request.POST.get("id")

        # cheching if item exists
        item = get_object_or_404(Claim, id=id, org=org)
        if item:

            # check role
            if profile.role not in ["admin", "staff"]:
                messages.error(request, "Permission denied")
                return redirect('dashboard')

            # save status
            item.status = status
            item.save()
            return redirect('claimmers')

    context = {
        'profile':profile,
        'claimmers':claimmers,
        'status':status
    }
    return render(request, 'users/claimmers.html', context)


# for claiming items
@login_required(login_url='login')
def ClaimItems(request, pk):
    
    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # get claimmer org
    org = profile.org

    # get items
    item = get_object_or_404(Item, org=org, id=pk)

    existing_claim = Claim.objects.filter(item=item, claimant=profile.user).exists()
    if existing_claim:
        messages.error(
            request, "You already submitted a claim for this item.")
        return redirect('dashboard')
    
    if item.status == "claimed":
        messages.error(request, "This item has already been claimed")
        return redirect("dashboard")

    # getting claimer input
    if request.method == 'POST':
        note = request.POST.get('note')

        # creatting claim
        Claim.objects.create(
            item_id=item.id,
            claimant_id=profile.user.id,
            org_id=org.id,
            proof=note,
            contact_phone=profile.phone_number,
            contact_email=profile.user.email
        )
        return redirect('dashboard')

    context = {
        'profile':profile,
        'item':item,
    }
    return render(request, 'users/claim.html', context)


# for searching items
@login_required(login_url='login')
def SearchItems(request):
    
    # get user org
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # get all user in the same org
    org = profile.org
    users = Profile.objects.filter(org=org)

    # searching for items(filtering)
    items = Item.objects.none()
    if request.method == 'POST':
        query = request.POST.get('query','')
        items = Item.objects.filter(org=org).filter(
            Q(name__icontains=query) |
            Q(category__icontains=query) |
            Q(status__icontains=query)
        )

    # get all items
    allItems = Item.objects.filter(org=org)

    context = {
        'profile':profile,
        'allItems':allItems,
        'query': items,
    }
    return render(request, 'users/search.html', context)


"""

---------- ADMIN SECTION -----------
The below functions is for admin end

"""


# for searching items
@login_required(login_url='login')
@CheckUser
def AdminPage(request):

    # getting all org
    allorg = Org.objects.all()
    activeorg = Org.objects.filter(status='active')
    inactiveorg = Org.objects.filter(status='inactive')
    suspended = Org.objects.filter(status='suspended')

    # importing choices
    status = Org.STATUS_CHOICES

    # for filtered org
    filterOrg = ''

    if request.method == 'POST':

        # searching for org(filtering)
        if 'orgs' in request.POST:

            # searching for org(filtering)
            query = request.POST.get('query','')
            filterOrg = Org.objects.filter(
                Q(orgname__icontains=query) |
                Q(status__icontains=query) |
                Q(subdomain__icontains=query) |
                Q(plan__name__icontains=query)
            )

        # editting org status
        elif 'update_status' in request.POST:
                
            # for changing org status
            status = request.POST.get("status")
            id = request.POST.get("id")

            # cheching if item exists
            org = get_object_or_404(Org, id=id)
            if org:
                org.status = status
                org.save()
                messages.success(request, f"{org.orgname} status updated successfully")
                return redirect('adminpage')

    context = {
        'status':status,
        'allorg':allorg,
        'activeorg':activeorg,
        'inactiveorg':inactiveorg,
        'suspended':suspended,
        'query':filterOrg,
    }
    return render(request, 'admin/admin.html', context)


# for searching items
@login_required(login_url='login')
@CheckUser
def AdminSettings(request):

    # get admin
    profile = request.user

    # for getting all plans
    plan = Plan.objects.all()

    # for edding plan
    if request.method == 'POST':
        amount = request.POST.get("amount")
        id = request.POST.get("id")

        # cheching if plan exists
        plan = Plan.objects.get(id=id)
        if plan:
            plan.amount = amount
            plan.save()
            return redirect('adminsetting')
        
    context = {
        'profile':profile,
        'plan':plan,
    }
    return render(request, 'admin/adminSetting.html', context)


# for active org
@login_required(login_url='login')
@CheckUser
def ActiveOrgs(request):

    # getting all org
    activeorg = Org.objects.filter(status='active')
    
    # importing choices
    status = Org.STATUS_CHOICES

    if request.method == 'POST':
        status = request.POST.get("status")
        id = request.POST.get("id")

        # cheching if item exists
        org = Org.objects.get(id=id)
        if org:
            org.status = status
            org.save()
            return redirect('adminpage')
        
    context = {
        'status':status,
        'activeorg':activeorg,
    }
    return render(request, 'admin/activeOrg.html', context)


# for inactive orgs
@login_required(login_url='login')
@CheckUser
def InactiveOrgs(request):
    
    # getting all org
    inactiveorg = Org.objects.filter(status='inactive')
    
    # importing choices
    status = Org.STATUS_CHOICES

    if request.method == 'POST':
        status = request.POST.get("status")
        id = request.POST.get("id")

        # cheching if item exists
        org = Org.objects.get(id=id)
        if org:
            org.status = status
            org.save()
            return redirect('adminpage')
        
    context = {
        'status':status,
        'inactiveorg':inactiveorg,
    }
    return render(request, 'admin/inactiveOrg.html', context)


# for suspendend orgs
@login_required(login_url='login')
@CheckUser
def SuspendedOrgs(request):
    
    # getting all org
    suspendedorg = Org.objects.filter(status='suspended')
    
    # importing choices
    status = Org.STATUS_CHOICES

    if request.method == 'POST':
        status = request.POST.get("status")
        id = request.POST.get("id")

        # cheching if item exists
        org = Org.objects.get(id=id)
        if org:
            org.status = status
            org.save()
            return redirect('adminpage')
        
    context = {
        'status':status,
        'suspendedorg':suspendedorg,
    }
    return render(request, 'admin/suspendedOrg.html', context)


# for admin deleting orgs
@login_required(login_url='login')
@CheckUser
def AdminDeleteOrg(request, pk):
    
    # checking if org exist
    deleteorg = get_object_or_404(Org, id=pk)
    if not deleteorg:
        return redirect('adminpage')
    
    # deleting org
    deleteorg.delete()
    return redirect('adminpage')


# for emailing orgs
@login_required(login_url='login')
@CheckUser
def EmailOrgs(request, pk):
    
    # get org id
    org = get_object_or_404(Org, id=pk)

    if request.method == 'POST':
        subject = request.POST.get("subject")
        note = request.POST.get("note")

        # cheching if item exists
        org = get_object_or_404(Org, id=pk)
        if org:

            # calling sending mail functionn here after creating account
            subject = subject
            extra_context={
                'note':note
            }
            SendMail(org.owner, 'extends/orgMail.html', subject, extra_context)

    context = {
        'org':org,
    }
    return render(request, 'admin/sendMail.html', context)


# for sending general email to orgs
@login_required(login_url='login')
@CheckUser
def GeneralEmail(request):

    # cheching if item exists
    orgs = Org.objects.all()

    if request.method == 'POST':
        subject = request.POST.get("subject")
        note = request.POST.get("note")

        # cheking if org exist
        if orgs.exists():

            sent_count = 0

            for org in orgs:
                if org.owner and org.owner.email:

                    # calling sending mail functionn here after creating account
                    extra_context={
                        'note':note
                    }

                    SendMail(org.owner, 'extends/generalMail.html', subject, extra_context)

                    sent_count += 1
            
            return HttpResponse(f'sent emails to {sent_count}orgs')

    context = {
        'orgs':orgs,
    }
    return render(request, 'admin/generalMail.html', context)



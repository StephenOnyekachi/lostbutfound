
from django.urls import path
from . import views

urlpatterns = [
    path('', views.Index, name='index'),
    path('login/', views.UserLogin, name='login'),
    path('signup/', views.OrgSignup, name='signup'),
    path('<str:subdomain>/register/', views.UserSignup, name='register'),
    path('logout/', views.UserLogout, name='logout'),

    path('dashboard/', views.Dashboard, name='dashboard'),
    path('orgprofile/', views.OrgProfile, name='orgprofile'),
    path('deleteorg/<int:pk>/', views.DeleteOrg, name='deleteorg'),
    path('payments/', views.Payments, name='payments'),
    path('renewpayment/', views.RenewPayment, name='renewpayment'),

    path('orgusers/', views.OrgUsers, name='orgusers'),
    path('deleteuser/<int:pk>/', views.DeleteUser, name='deleteuser'),

    path('founditems/', views.FoundItems, name='founditems'),
    path('claimeditems/', views.ClaimedItems, name='claimeditems'),
    path('additem/', views.AddItems, name='additem'),
    path('claimmers/', views.Claimmers, name='claimmers'),
    path('claimitem/<int:pk>/', views.ClaimItems, name='claimitem'),
    path('deleteitem/<int:pk>/', views.DeleteItem, name='deleteitem'),
    path('searchitem/', views.SearchItems, name='searchitem'),

    path('adminpage/', views.AdminPage, name='adminpage'),
    path('adminsetting/', views.AdminSettings, name='adminsetting'),
    path('activeorg/', views.ActiveOrgs, name='activeorg'),
    path('inactiveorg/', views.InactiveOrgs, name='inactiveorg'),
    path('suspendedorg/', views.SuspendedOrgs, name='suspendedorg'),
    path('emailorg/<int:pk>/', views.EmailOrgs, name='emailorg'),
    path('generalemail/', views.GeneralEmail, name='generalemail'),
    path('admindeleteorg/<int:pk>/', views.AdminDeleteOrg, name='admindeleteorg'),
]
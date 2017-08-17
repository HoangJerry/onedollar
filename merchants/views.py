from django.shortcuts import render, get_object_or_404, redirect
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone, formats
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.text import Truncator

def index(request):
    return render(request, 'merchants/index.html', {})
    
def welcome(request):
    return render(request, 'merchants/welcome.html', {'fixed_width' : 'fixed-width', 'displayNone' : 'none'})

def login(request):
    return render(request, 'merchants/login.html', {'displayNone' : 'none'})
    
def logout(request):
    return render(request, 'merchants/logout.html', {})
    
def register(request):
    return render(request, 'merchants/register.html', {'fixed_width' : 'fixed-width', 'displayNone' : 'none'})    
    
def register_step2(request):
    return render(request, 'merchants/register_step2.html', {'fixed_width' : 'fixed-width', 'displayNone' : 'none'})    
    
def register_step3(request):
    return render(request, 'merchants/register_step3.html', {'fixed_width' : 'fixed-width', 'displayNone' : 'none'})    

def forget_password(request):
    return render(request, 'merchants/forget_password.html', {'displayNone' : 'none'})

def reset_password(request):
    return render(request, 'merchants/reset_password.html', {'fixed_width' : 'fixed-width', 'displayNone' : 'none'})

def account_validated(request):
    return render(request, 'merchants/account_validated.html', {})
    
def request_confirmation_by_phone(request):
    return render(request, 'merchants/request_confirmation_by_phone.html', {})   
     
def terms_of_service(request):
    return render(request, 'merchants/terms_of_service.html', {})     
    
def payment_settings(request):
    return render(request, 'merchants/payment_settings.html', {})

def payment_history(request):
    return render(request, 'merchants/payment_history.html', {})
    
def add_products(request):
    return render(request, 'merchants/add_products.html', {})    

def edit_products(request):
    return render(request, 'merchants/edit_products.html', {})
    
def product(request):
    return render(request, 'merchants/product.html', {})    

def order_history(request):
    return render(request, 'merchants/order_history.html', {})

# Account Settings
def general_information(request):
    return render(request, 'merchants/general_information.html', {})

def email_preferences(request):
    return render(request, 'merchants/email_preferences.html', {})
    
def display_settings(request):
    return render(request, 'merchants/display_settings.html', {})
    
def change_username(request):
    return render(request, 'merchants/change_username.html', {})
    
def change_password(request):
    return render(request, 'merchants/change_password.html', {})    

def change_email(request):
    return render(request, 'merchants/change_email.html', {})
    
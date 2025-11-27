from django.shortcuts import render,redirect
from django.contrib.auth.views import *
from . forms import*
from django.contrib.auth import authenticate,login,logout
# Create your views here.
class Login(LoginView):
    form_class=EmailAuthenticationForm
    template_name="login.html"
    redirect_authenticated_user=True

def inscription(request):
    if  request.user.is_authenticated:
         return redirect ("chatbot:chat")
    if request.method=="POST":
     form=UserCreationForm(request.POST)
     first_name=request.POST["first_name"]
     last_name=request.POST["last_name"]
     email=request.POST["email"]
     password1=request.POST["password1"]
     if User.objects.filter(username=f'{first_name} {last_name}').exists() or User.objects.filter(first_name=first_name).exists() or User.objects.filter(last_name=last_name).exists() or User.objects.filter(email=email).exists() or User.objects.filter(password=password1).exists():
         User.objects.create_user(username=f'{first_name} {last_name}',email=email,password=password1,first_name=first_name,last_name=last_name)
     else:
        User.objects.create_user(username=f'{first_name} {last_name}',email=email,password=password1,first_name=first_name,last_name=last_name)
         
     user=authenticate(request,username=f'{first_name} {last_name}',password=password1)
     if user is not None:
         login(request,user)
         return redirect("chatbot:chat")
    form=UserForm()

    context={"form":form
             }
    return render(request,'inscription.html',context=context)
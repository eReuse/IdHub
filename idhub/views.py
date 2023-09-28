from django.shortcuts import render
from .models import User


from django.shortcuts import redirect, render

def index(request):
    return redirect("/user")


def user(request):
    uid = request.user
    user = User.get(uid)
    context = { userdata: user }
    return render(request, "polls/user.html", context)
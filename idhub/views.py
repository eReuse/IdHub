from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .models import AppUser
from .forms import UserForm
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required


def index(request):
    return redirect("/user")


@login_required
def user(request):
    current_user: AppUser = request.user.appuser
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            cdata = form.cleaned_data
            current_user.django_user.first_name = cdata['first_name']
            current_user.save()
            current_user.django_user.save()
            return HttpResponseRedirect(reverse("user"))
        else:
            return render(request, "idhub/user-details.html", {"form": form})
    elif request.method == "GET":
        form = UserForm.from_user(current_user)
        return render(request, "idhub/user-details.html", {"form": form})

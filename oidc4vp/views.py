from django.shortcuts import render

class PeopleEditView(People, FormView):
    template_name = "idhub/admin/user_edit.html"
    form_class = ProfileForm
    success_url = reverse_lazy('idhub:admin_people_list')


    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, _('The credential was sended successfully'))
        # Event.set_EV_USR_UPDATED_BY_ADMIN(user)
        # Event.set_EV_USR_UPDATED(user)

        return super().form_valid(form)



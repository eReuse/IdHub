from django.conf import settings
from django.template import loader
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class NotifyActivateUserByEmail:
    def get_email_context(self, user):
        """
        Define a new context with a token for put in a email
        when send a email for add a new password  
        """
        protocol = 'https' if self.request.is_secure() else 'http'
        current_site = get_current_site(self.request)
        site_name = current_site.name
        domain = current_site.domain
        context = {
            'email': user.email,
            'domain': domain,
            'site_name': site_name,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'user': user,
            'token': default_token_generator.make_token(user),
            'protocol': protocol,
        }
        return context

    def send_email(self, user):
        """
        Send a email when a user is activated.
        """
        context = self.get_email_context(user)
        subject_template_name = 'idhub/admin/registration/activate_user_subject.txt'
        email_template_name = 'idhub/admin/registration/activate_user_email.txt'
        html_email_template_name = 'idhub/admin/registration/activate_user_email.html'
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email

        email_message = EmailMultiAlternatives(
            subject, body, from_email, [to_email])
        html_email = loader.render_to_string(html_email_template_name, context)
        email_message.attach_alternative(html_email, 'text/html')
        if settings.DEVELOPMENT:
            print(to_email)
            print(body)
            return

        email_message.send()

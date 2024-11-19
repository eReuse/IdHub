import logging

from django.conf import settings
from django.template import loader
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


logger = logging.getLogger(__name__)


class NotifyActivateUserByEmail:
    subject_template_name = 'activate_user_subject.txt'
    email_template_name = 'activate_user_email.txt'
    html_email_template_name = 'activate_user_email.html'

    def get_email_context(self, user, token):
        """
        Define a new context with a token for put in a email
        when send a email for add a new password  
        """
        protocol = 'https' if self.request.is_secure() else 'http'
        current_site = get_current_site(self.request)
        site_name = current_site.name
        domain = current_site.domain
        if not token:
            token = default_token_generator.make_token(user)

        context = {
            'email': user.email,
            'domain': domain,
            'site_name': site_name,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'user': user,
            'token': token,
            'protocol': protocol,
        }
        return context

    def send_email(self, user, token=None):
        """
        Send a email when a user is activated.
        """
        context = self.get_email_context(user, token)
        subject = loader.render_to_string(self.subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(self.email_template_name, context)
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email

        email_message = EmailMultiAlternatives(
            subject, body, from_email, [to_email])
        html_email = loader.render_to_string(self.html_email_template_name, context)
        email_message.attach_alternative(html_email, 'text/html')
        try:
            if settings.ENABLE_EMAIL:
                email_message.send()
                return

            logger.warning(to_email)
            logger.warning(body)

        except Exception as err:
            logger.error(err)
            return

import logging

from django.conf import settings
from django.template import loader
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = "Send mails to the admins for add general key"
    subject_template_name = 'idhub/admin/registration/start_app_admin_subject.txt'
    email_template_name = 'idhub/admin/registration/start_app_admin_email.txt'
    html_email_template_name = 'idhub/admin/registration/start_app_admin_email.html'

    def handle(self, *args, **kwargs):
        for user in User.objects.filter(is_admin=True):
            self.send_email(user)

    def send_email(self, user):
        """
        Send a email when a user is activated.
        """
        url_domain = "https://{}/".format(settings.DOMAIN)
        context = {
            "domain": settings.DOMAIN,
            "url_domain": url_domain,
        }
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

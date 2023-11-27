from django.db import models


class VPVerifyRequest(models.Model):
    """
    `nonce` is an opaque random string used to lookup verification requests. URL-safe.
      Example: "UPBQ3JE2DGJYHP5CPSCRIGTHRTCYXMQPNQ"
    `expected_credentials` is a JSON list of credential types that must be present in this VP.
      Example: ["FinancialSituationCredential", "HomeConnectivitySurveyCredential"]
    `expected_contents` is a JSON object that places optional constraints on the contents of the
      returned VP.
      Example: [{"FinancialSituationCredential": {"financial_vulnerability_score": "7"}}]
    `action` is (for now) a JSON object describing the next steps to take if this verification
      is successful. For example "send mail to <destination> with <subject> and <body>"
      Example: {"action": "send_mail", "params": {"to": "orders@somconnexio.coop", "subject": "New client", "body": ...}
    `response` is a URL that the user's wallet will redirect the user to.
    `submitted_on` is used (by a cronjob) to purge old entries that didn't complete verification
    """
    nonce = models.CharField(max_length=50)
    expected_credentials = models.CharField(max_length=255)
    expected_contents = models.TextField()
    action = models.TextField()
    response_or_redirect = models.CharField(max_length=255)
    submitted_on = models.DateTimeField(auto_now=True)

"""``WalletForm`` and ``ContractForm``.

``WalletForm`` is the one that matters: its ``save()`` is what creates the
``Authorization`` and the ``Promotion`` behind a discount, and it returns the
url the browser is sent to. ``ContractForm`` is ten free-text fields.
"""
from django.test import override_settings

from oidc4vp.models import Authorization, Organization
from promotion.forms import ContractForm, WalletForm
from promotion.models import Promotion
from test_support.base import IdHubBaseTestCase


PRESENTATION = '["MembershipCard"]'


def contract_data(**overrides):
    data = {
        'nif': '12345678Z',
        'name': 'Ana',
        'first_last_name': 'Pérez',
        'second_last_name': 'García',
        'email': 'ana@example.org',
        'email_repeat': 'ana@example.org',
        'telephone': '600000000',
        'birthday': '1980-01-01',
        'gen': 'female',
        'lang': 'ca',
    }
    data.update(overrides)
    return data


class WalletFormTest(IdHubBaseTestCase):
    def setUp(self):
        super().setUp()
        self.org = Organization.objects.create(
            name='Peer',
            domain='peer.example.org',
            response_uri='https://peer.example.org/oidc4vp/',
            my_client_id='my-client-id',
            my_client_secret='my-client-secret',
        )

    def form(self, organization=None, presentation=PRESENTATION):
        return WalletForm(
            data={'organization': organization or self.org.id},
            presentation_definition=presentation,
        )

    def test_our_own_organization_is_not_offered_as_a_wallet(self):
        Organization.objects.create(name='Us', domain='testserver')

        choices = dict(self.form().fields['organization'].choices)

        self.assertEqual(list(choices.values()), ['Peer'])

    def test_an_organization_without_a_domain_is_offered(self):
        # The exclusion is by domain, and the column defaults to None, so a row
        # created without one is not us and not excluded. init_org does write
        # the domain, but anything that creates an Organization by hand ends up
        # in the wallet list.
        Organization.objects.create(name='No domain')

        choices = dict(self.form().fields['organization'].choices)

        self.assertEqual(sorted(choices.values()), ['No domain', 'Peer'])

    def test_saving_returns_the_authorize_url_of_the_chosen_wallet(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)

        url = form.save()

        self.assertTrue(
            url.startswith('https://peer.example.org/oidc4vp/authorize?'), url
        )

    def test_saving_leaves_an_authorization_and_a_promotion_linked(self):
        form = self.form()
        form.is_valid()

        form.save()

        authorization = Authorization.objects.get()
        self.assertEqual(authorization.organization, self.org)
        self.assertEqual(authorization.presentation_definition, PRESENTATION)
        self.assertEqual(Promotion.objects.get().authorize, authorization)

    def test_the_promotion_is_created_without_a_name(self):
        # `name` is a required CharField and save() does not pass one, so every
        # promotion the flow creates is listed as the empty string. Nothing
        # reads it today, which is why it has gone unnoticed.
        form = self.form()
        form.is_valid()
        form.save()

        self.assertEqual(Promotion.objects.get().name, '')

    def test_the_promotion_is_the_only_type_there_is(self):
        form = self.form()
        form.is_valid()
        form.save()

        self.assertEqual(
            Promotion.objects.get().discount, Promotion.Types.VULNERABLE
        )

    def test_without_committing_nothing_is_written_and_no_url_comes_back(self):
        form = self.form()
        form.is_valid()

        self.assertIsNone(form.save(commit=False))
        self.assertFalse(Authorization.objects.exists())
        self.assertFalse(Promotion.objects.exists())

    def test_an_organization_that_does_not_exist_gives_no_url(self):
        # Unreachable through SelectWalletView, because the ChoiceField
        # validates against the same queryset the form built. It is the only
        # guard save() has, so it is pinned here.
        self.assertIsNone(WalletForm(
            data={'organization': 999}, presentation_definition=PRESENTATION
        ).save())

    def test_choosing_nothing_is_a_form_error(self):
        form = WalletForm(data={}, presentation_definition=PRESENTATION)

        self.assertFalse(form.is_valid())
        self.assertIn('organization', form.errors)

    @override_settings(SUPPORTED_CREDENTIALS=['MembershipCard'])
    def test_the_presentation_definition_is_stored_verbatim(self):
        form = self.form(presentation='["MembershipCard", "CourseCredential"]')
        form.is_valid()
        form.save()

        self.assertEqual(
            Authorization.objects.get().presentation_definition,
            '["MembershipCard", "CourseCredential"]',
        )


class ContractFormTest(IdHubBaseTestCase):
    def test_a_filled_in_contract_is_valid(self):
        form = ContractForm(data=contract_data())

        self.assertTrue(form.is_valid(), form.errors)

    def test_every_single_field_is_required(self):
        for field in contract_data():
            with self.subTest(field=field):
                form = ContractForm(data=contract_data(**{field: ''}))

                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_the_repeated_address_is_never_compared_with_the_first_one(self):
        # There is no clean(), so the field is decoration: a typo in either box
        # is accepted and whoever consumes the contract gets two addresses.
        form = ContractForm(data=contract_data(email_repeat='other@example.org'))

        self.assertTrue(form.is_valid(), form.errors)

    def test_none_of_the_fields_is_validated_for_what_it_holds(self):
        # All ten are plain CharFields: the email is not an EmailField and the
        # birthday is not a DateField, so anything that is not empty passes.
        form = ContractForm(data=contract_data(
            email='not an address', birthday='yesterday', telephone='n/a',
        ))

        self.assertTrue(form.is_valid(), form.errors)

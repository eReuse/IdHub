"""``ProfileForm``: the form the admin uses to create and edit people.

Two things make it worth testing. Its ``clean_`` methods decide what a person
is allowed to be called, which is a rule that rejects more than its error
message says; and ``is_admin`` is one of its fields, so this is the form that
grants administrator rights.
"""
from django.test import TestCase

from idhub_auth.forms import ProfileForm
from idhub_auth.models import User


def form(**overrides):
    data = {
        'first_name': 'Ana',
        'last_name': 'Pérez',
        'email': 'ana@example.org',
        'is_admin': False,
    }
    data.update(overrides)
    return ProfileForm(data=data)


class ProfileFormTest(TestCase):
    def test_a_filled_in_form_creates_the_person(self):
        f = form()

        self.assertTrue(f.is_valid(), f.errors)
        user = f.save()
        self.assertEqual(user.first_name, 'Ana')
        self.assertEqual(user.email, 'ana@example.org')
        self.assertFalse(user.is_admin)

    def test_this_is_the_form_that_hands_out_administrator_rights(self):
        # is_admin is a plain field of the form: whoever can post it can grant
        # it. What keeps that in check is the guard on the two admin views that
        # use the form, not the form itself.
        user = form(is_admin=True).save()

        self.assertTrue(user.is_admin)

    def test_the_accented_letters_of_the_pilot_languages_are_accepted(self):
        for name in ('Müller', 'Nuñez', 'Çelik', 'Ferreño', 'Òdena'):
            with self.subTest(name=name):
                self.assertTrue(form(last_name=name).is_valid())

    def test_a_double_barrelled_name_is_accepted(self):
        self.assertTrue(form(last_name="Vall d'Hebron-Sarrià").is_valid())

    def test_an_initial_with_a_dot_is_rejected(self):
        # The regex has no dot, so the usual way of writing a middle name does
        # not get through. The message only talks about "characters and
        # spaces", which does not help whoever typed it.
        f = form(first_name='Ana M. José')

        self.assertFalse(f.is_valid())
        self.assertEqual(
            f.errors['first_name'],
            ['The string must contain only characters and spaces'],
        )

    def test_a_digit_is_rejected(self):
        self.assertFalse(form(last_name='Pérez 2').is_valid())

    def test_a_name_in_another_alphabet_is_rejected(self):
        # Only the latin letters listed in the pattern are allowed, so a
        # cyrillic or greek name cannot be registered at all.
        for name in ('Иванов', 'Παπαδόπουλος', '李'):
            with self.subTest(name=name):
                self.assertFalse(form(last_name=name).is_valid())

    def test_an_empty_name_is_a_required_error_and_not_a_crash(self):
        # clean_first_name() reads cleaned_data['first_name'] without a guard,
        # which is the shape that breaks six forms in the admin. Here it is
        # safe: Django skips clean_<field> when the field itself failed.
        f = form(first_name='')

        self.assertFalse(f.is_valid())
        self.assertEqual(f.errors['first_name'], ['This field is required.'])

    def test_a_name_of_only_spaces_is_empty_after_the_strip(self):
        f = form(first_name='   ')

        self.assertFalse(f.is_valid())
        self.assertEqual(f.errors['first_name'], ['This field is required.'])

    def test_the_surrounding_spaces_are_dropped(self):
        f = form(first_name='  Ana  ')

        self.assertTrue(f.is_valid(), f.errors)
        self.assertEqual(f.cleaned_data['first_name'], 'Ana')

    def test_an_address_somebody_already_uses_is_refused(self):
        User.objects.create_user(email='ana@example.org', password='anapass12')

        f = form()

        self.assertFalse(f.is_valid())
        self.assertEqual(
            f.errors['email'], ['User with this Email address already exists.']
        )

    def test_editing_a_person_keeps_their_own_address(self):
        user = User.objects.create_user(email='ana@example.org', password='anapass12')

        f = ProfileForm(
            instance=user,
            data={
                'first_name': 'Ana',
                'last_name': 'Pérez',
                'email': 'ana@example.org',
                'is_admin': False,
            },
        )

        self.assertTrue(f.is_valid(), f.errors)

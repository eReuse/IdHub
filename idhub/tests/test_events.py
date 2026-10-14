"""The Event.set_EV_* constructors.

There are thirty-four of them and they all do the same two things: build a
message and insert a row. The table below drives one assertion per
constructor; the tests after it pin the handful that misbehave.
"""
from idhub.models import DID, Event
from test_support import factories
from test_support.base import IdHubTestCase


# (type name, argument spec, whether the row is attached to a user)
#
# The constructor is named after the type, so the expected type is derived
# from the first column instead of being repeated.
EVENTS = [
    ('EV_USR_REGISTERED', 'user', False),
    ('EV_USR_WELCOME', 'user', True),
    ('EV_DATA_UPDATE_REQUESTED_BY_USER', 'user', False),
    ('EV_DATA_UPDATE_REQUESTED', 'user', True),
    ('EV_USR_UPDATED_BY_ADMIN', 'user', False),
    ('EV_USR_UPDATED', 'user', True),
    ('EV_USR_DELETED_BY_ADMIN', 'user', False),
    ('EV_DID_CREATED_BY_USER', 'did', False),
    ('EV_DID_CREATED', 'did', True),
    ('EV_DID_DELETED', 'did', True),
    ('EV_CREDENTIAL_DELETED_BY_ADMIN', 'cred', False),
    ('EV_CREDENTIAL_DELETED', 'cred', True),
    ('EV_CREDENTIAL_ISSUED_FOR_USER', 'cred', False),
    ('EV_CREDENTIAL_ISSUED', 'cred', True),
    ('EV_CREDENTIAL_PRESENTED_BY_USER', 'cred verifier', False),
    ('EV_CREDENTIAL_PRESENTED', 'cred verifier', True),
    ('EV_CREDENTIAL_ENABLED', 'cred', False),
    ('EV_CREDENTIAL_CAN_BE_REQUESTED', 'cred', True),
    ('EV_CREDENTIAL_REVOKED_BY_ADMIN', 'cred', False),
    ('EV_CREDENTIAL_REVOKED', 'cred', True),
    ('EV_ROLE_CREATED_BY_ADMIN', '', False),
    ('EV_ROLE_MODIFIED_BY_ADMIN', '', False),
    ('EV_ROLE_DELETED_BY_ADMIN', '', False),
    ('EV_SERVICE_CREATED_BY_ADMIN', '', False),
    ('EV_SERVICE_MODIFIED_BY_ADMIN', '', False),
    ('EV_SERVICE_DELETED_BY_ADMIN', '', False),
    ('EV_ORG_DID_CREATED_BY_ADMIN', 'org_did', False),
    ('EV_ORG_DID_DELETED_BY_ADMIN', 'org_did', False),
    ('EV_USR_DEACTIVATED_BY_ADMIN', 'user', False),
    ('EV_USR_ACTIVATED_BY_ADMIN', 'user', False),
    ('EV_USR_SEND_VP', 'message user', True),
    ('EV_USR_SEND_CREDENTIAL', 'message', False),
    ('EV_SCHEME_UPLOAD', 'message', False),
    ('EV_USR_CRED_TO_DLT', 'message', False),
]

MESSAGE = 'A message written by the caller'

# set_EV_SCHEME_UPLOAD never passes its argument on to create().
WITHOUT_MESSAGE = {'EV_SCHEME_UPLOAD'}


class EventConstructorsTest(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.user.first_name = 'Dummy'
        self.user.last_name = 'User'
        self.user.save()
        self.did = factories.make_did(label='Personal', user=self.user)
        self.org_did = factories.make_did(label='Organisational')
        self.schema = factories.make_schema('membership-card.json')
        self.cred = factories.make_credential(self.user, self.schema, self.org_did)
        self.verifier = 'https://verifier.example.org'
        self.message = MESSAGE

    def call(self, type_name, spec):
        args = [getattr(self, name) for name in spec.split()]
        getattr(Event, 'set_{}'.format(type_name))(*args)
        return Event.objects.get(type=Event.Types[type_name])

    def test_each_constructor_stores_its_own_type(self):
        for type_name, spec, _owned in EVENTS:
            with self.subTest(event=type_name):
                event = self.call(type_name, spec)
                self.assertEqual(event.type, Event.Types[type_name])

    def test_only_the_user_facing_events_are_attached_to_a_user(self):
        # The admin copy of an event is deliberately userless: the lists in
        # the admin area show every event with user=None.
        for type_name, spec, owned in EVENTS:
            with self.subTest(event=type_name):
                event = self.call(type_name, spec)
                self.assertEqual(event.user, self.user if owned else None)

    def test_every_message_is_filled_in(self):
        for type_name, spec, _owned in EVENTS:
            if type_name in WITHOUT_MESSAGE:
                continue
            with self.subTest(event=type_name):
                event = self.call(type_name, spec)
                self.assertTrue(event.message.strip())
                self.assertNotIn('{', event.message)
                self.assertNotIn('}', event.message)

    def test_the_messages_carry_the_data_they_were_given(self):
        specs = dict((type_name, spec) for type_name, spec, _ in EVENTS)
        expected = [
            ('EV_USR_REGISTERED', self.USER_EMAIL),
            ('EV_USR_WELCOME', 'Dummy'),
            ('EV_DID_CREATED', 'Personal'),
            ('EV_DID_CREATED_BY_USER', self.did.did),
            ('EV_ORG_DID_CREATED_BY_ADMIN', self.org_did.did),
            ('EV_CREDENTIAL_ISSUED', self.cred.type),
            ('EV_CREDENTIAL_PRESENTED', self.verifier),
            ('EV_USR_SEND_VP', MESSAGE),
        ]
        for type_name, fragment in expected:
            with self.subTest(event=type_name):
                event = self.call(type_name, specs[type_name])
                self.assertIn(fragment, event.message)


class EventCoverageTest(IdHubTestCase):
    def test_only_one_type_has_no_constructor(self):
        # EV_CREDENTIAL_DELETED_BY_USER is in the enum and in the templates,
        # but nothing ever writes a row with it.
        missing = set(
            type.name for type in Event.Types
            if not hasattr(Event, 'set_{}'.format(type.name))
        )
        self.assertEqual(missing, {'EV_CREDENTIAL_DELETED_BY_USER'})

    def test_the_table_covers_every_constructor(self):
        self.assertEqual(
            set(type_name for type_name, _spec, _owned in EVENTS),
            set(type.name for type in Event.Types) -
            {'EV_CREDENTIAL_DELETED_BY_USER'},
        )

    def test_get_type_name_is_the_label_of_every_type(self):
        for type in Event.Types:
            with self.subTest(type=type.name):
                self.assertEqual(Event(type=type.value).get_type_name(), type.label)

    def test_get_type_name_rejects_a_type_outside_the_enum(self):
        with self.assertRaises(ValueError):
            Event(type=999).get_type_name()


class EventMessageQuirksTest(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema('membership-card.json')
        self.did = factories.make_did(label='Org', type=DID.Types.KEY)
        self.cred = factories.make_credential(self.user, self.schema, self.did)

    def test_scheme_upload_throws_its_message_away(self):
        # The argument is accepted and then not forwarded to create(), so the
        # admin event log shows an empty description for every schema upload.
        Event.set_EV_SCHEME_UPLOAD('Uploaded membership-card.json')
        self.assertEqual(
            Event.objects.get(type=Event.Types.EV_SCHEME_UPLOAD).message, ''
        )

    def test_revoked_by_admin_names_no_one(self):
        # The message ends in "was revoked for " with nothing after it: the
        # username was never interpolated.
        Event.set_EV_CREDENTIAL_REVOKED_BY_ADMIN(self.cred)
        message = Event.objects.get(
            type=Event.Types.EV_CREDENTIAL_REVOKED_BY_ADMIN
        ).message
        self.assertTrue(message.endswith('was revoked for '))
        self.assertNotIn(self.USER_EMAIL, message)

    def test_the_concatenated_messages_are_never_translatable(self):
        # Half a dozen constructors build the message with += and then wrap
        # the result in gettext. The composed string is not in any .po file,
        # so those events stay in english whatever the active language is.
        Event.set_EV_USR_UPDATED_BY_ADMIN(self.user)
        self.assertIn(
            "The admin has updated the following user 's information: ",
            Event.objects.get(type=Event.Types.EV_USR_UPDATED_BY_ADMIN).message,
        )

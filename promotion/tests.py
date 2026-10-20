"""The Promotion model.

Two methods, both pure. The discount is applied by ContractView to the
hardcoded prices in its context.
"""
from django.test import SimpleTestCase

from promotion.models import Promotion


class PromotionTest(SimpleTestCase):
    def test_get_discount_takes_a_quarter_off(self):
        self.assertEqual(Promotion(name='p').get_discount(100), 75.0)
        self.assertEqual(Promotion(name='p').get_discount(0), 0.0)

    def test_get_discount_ignores_the_discount_field(self):
        # `discount` holds a Types value and the only method that could read
        # it does not: the 25% is hardcoded, so adding a second promotion type
        # would need a code change, not a new row.
        for discount in (None, Promotion.Types.VULNERABLE):
            with self.subTest(discount=discount):
                promotion = Promotion(name='p', discount=discount)
                self.assertEqual(promotion.get_discount(20), 15.0)

    def test_get_discount_returns_a_float(self):
        self.assertIsInstance(Promotion(name='p').get_discount(4), float)

    def test_get_url_hangs_the_code_off_the_contract_view(self):
        self.assertEqual(
            Promotion(name='p').get_url('abc123'),
            '/promotion/contract?code=abc123',
        )

    def test_get_url_does_not_escape_the_code(self):
        # The codes come from Authorization.code, which is generated from
        # SALT_CHARS, so nothing url-unsafe reaches this. A code carrying an
        # ampersand would silently add a second query parameter.
        self.assertEqual(
            Promotion(name='p').get_url('a&b=c'),
            '/promotion/contract?code=a&b=c',
        )

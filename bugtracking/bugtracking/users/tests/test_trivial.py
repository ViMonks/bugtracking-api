from django.test import TestCase
from model_bakery import baker


class TrivialTest(TestCase):

    def test_trivial(self):
        self.assertEqual(True, True)

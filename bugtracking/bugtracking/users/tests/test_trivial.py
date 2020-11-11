from django.test import TestCase


class TrivialTest(TestCase):

    def test_trivial(self):
        self.assertEqual(True, True)

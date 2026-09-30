from django.test import TestCase

from .models import Case, CaseItem, Skin
from .services import build_strip


class StripTests(TestCase):
    def setUp(self):
        self.case = Case.objects.create(slug='s', name='S', price=100)
        self.skins = [
            Skin.objects.create(key=f'k{i}', name=f'W{i}|S{i}', price=(i + 1) * 10,
                                image_url=f'https://x/{i}.png')
            for i in range(5)
        ]
        for i, s in enumerate(self.skins):
            CaseItem.objects.create(case=self.case, skin=s, weight=100 - i)

    def test_strip_size_respected(self):
        self.assertEqual(len(build_strip(self.case, size=40)), 40)

    def test_winner_appears_once_and_at_expected_slot(self):
        winner = self.skins[3]
        strip = build_strip(self.case, size=64, winner=winner)
        self.assertEqual(len(strip), 64)
        self.assertEqual(sum(1 for i in strip if i['id'] == winner.id), 1)
        self.assertEqual(strip[64 - 25]['id'], winner.id)

    def test_strip_without_winner_only_uses_case_items(self):
        ids = {s.id for s in self.skins}
        strip = build_strip(self.case, size=30)
        self.assertTrue({i['id'] for i in strip} <= ids)
        self.assertTrue(all(i['image'].startswith('https://x/') for i in strip))

    def test_empty_case_returns_empty_strip(self):
        empty = Case.objects.create(slug='e', name='E', price=1)
        self.assertEqual(build_strip(empty, size=64), [])
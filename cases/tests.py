from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Case, CaseItem, Drop, Profile, Promo, Skin


def make_case(price=100):
    case = Case.objects.create(slug='test', name='Test', price=price)
    for i, p in enumerate([10, 100, 1000]):
        skin = Skin.objects.create(
            key=f's{i}', name=f'W{i} | S{i}', weapon=f'W{i}', finish=f'S{i}',
            price=p, image_url=f'https://example.com/{i}.png',
        )
        CaseItem.objects.create(case=case, skin=skin, weight=1000000 / (p ** 1.35))
    return case


class SmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.case = make_case()

    def test_pages_render(self):
        for name, kwargs in [
            ('cases:home', {}),
            ('cases:case', {'slug': 'test'}),
            ('cases:top', {}),
            ('cases:faq', {}),
            ('cases:support', {}),
            ('cases:giveaways', {}),
            ('cases:tournaments', {}),
            ('cases:rule', {'kind': 'terms'}),
            ('login', {}),
            ('register', {}),
        ]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, kwargs=kwargs)).status_code, 200)

    def test_authed_pages(self):
        User.objects.create_user('bob', password='secret123')
        self.client.login(username='bob', password='secret123')
        Profile.objects.filter(user__username='bob').update(balance=5000)
        for name in ['cases:profile', 'cases:inventory', 'cases:upgrade',
                     'cases:contract']:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_register_creates_profile_with_balance(self):
        res = self.client.post(reverse('register'),
                               {'username': 'newbie', 'password': 'secret123'})
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Profile.objects.filter(user__username='newbie',
                                               balance=10000).exists())

    def test_open_case_charges_and_drops(self):
        carol = User.objects.create_user('carol', password='secret123')
        Profile.objects.filter(user=carol).update(balance=1000)
        self.client.login(username='carol', password='secret123')

        res = self.client.post(reverse('cases:api_open', args=['test']))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('skin', data)
        self.assertEqual(len(data['strip']), 64)

        p = Profile.objects.get(user=carol)
        self.assertEqual(p.balance, 900)
        self.assertEqual(Drop.objects.filter(user__username='carol').count(), 1)
        self.assertIn(data['skin']['id'], [i['id'] for i in data['strip']])

    def test_open_case_requires_login(self):
        res = self.client.post(reverse('cases:api_open', args=['test']))
        self.assertEqual(res.status_code, 403)

    def test_open_case_rejects_broke_user(self):
        User.objects.create_user('dave', password='secret123')
        self.client.login(username='dave', password='secret123')
        Profile.objects.filter(user__username='dave').update(balance=10)
        res = self.client.post(reverse('cases:api_open', args=['test']))
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error'], 'not_enough_balance')

    def test_cheaper_items_are_more_likely(self):
        from .services import _weighted_choice

        picks = [_weighted_choice(self.case.items.select_related('skin')).skin_id
                 for _ in range(400)]
        cheap = picks.count(self.case.items.order_by('skin__price').first().skin_id)
        dear = picks.count(self.case.items.order_by('-skin__price').first().skin_id)
        self.assertGreater(cheap, dear)

    def test_promo_redeem_once(self):
        User.objects.create_user('erin', password='secret123')
        self.client.login(username='erin', password='secret123')
        Profile.objects.filter(user__username='erin').update(balance=1000)
        Promo.objects.create(code='BONUS', amount=250)

        self.client.post(reverse('promo:redeem'), {'code': 'BONUS'})
        self.assertEqual(Profile.objects.get(user__username='erin').balance, 1250)

        self.client.post(reverse('promo:redeem'), {'code': 'BONUS'})
        self.assertEqual(Profile.objects.get(user__username='erin').balance, 1250)

    def test_upgrade_consumes_one_item_and_returns_winner(self):
        User.objects.create_user('frank', password='secret123')
        self.client.login(username='frank', password='secret123')
        from .models import InventoryItem

        skin = Skin.objects.get(key='s0')
        inv = InventoryItem.objects.create(
            user=User.objects.get(username='frank'), skin=skin)

        res = self.client.post(reverse('cases:api_upgrade_roll'), {
            'case': self.case.id, 'ratio': '1', 'item': inv.id,
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()

        inv.refresh_from_db()
        self.assertTrue(inv.consumed)
        self.assertEqual(data['input']['id'], skin.id)
        self.assertGreaterEqual(data['winner']['price'], skin.price)
        self.assertEqual(
            InventoryItem.objects.filter(user__username='frank', consumed=False).count(),
            1,
        )

    def test_upgrade_wheel_segments_respect_threshold(self):
        from .services import build_wheel

        wheel = build_wheel(self.case, 100, 2)
        self.assertTrue(wheel['possible'])
        self.assertEqual(wheel['threshold'], 200)
        prices = [s['price'] for s in wheel['segments']]
        self.assertTrue(all(p >= 200 for p in prices))
        self.assertAlmostEqual(sum(s['chance'] for s in wheel['segments']), 100, places=4)

    def test_upgrade_wheel_impossible_when_nothing_qualifies(self):
        from .services import build_wheel

        wheel = build_wheel(self.case, 100000, 5)
        self.assertFalse(wheel['possible'])
        self.assertEqual(wheel['segments'], [])

    def test_upgrade_roll_rejects_impossible_ratio(self):
        User.objects.create_user('ida', password='secret123')
        self.client.login(username='ida', password='secret123')
        from .models import InventoryItem

        inv = InventoryItem.objects.create(
            user=User.objects.get(username='ida'), skin=Skin.objects.get(key='s0'))

        res = self.client.post(reverse('cases:api_upgrade_roll'), {
            'case': self.case.id, 'ratio': '100', 'item': inv.id,
        })
        self.assertEqual(res.status_code, 400)
        inv.refresh_from_db()
        self.assertFalse(inv.consumed)

    def test_upgrade_roll_rejects_other_users_item(self):
        User.objects.create_user('owner', password='secret123')
        User.objects.create_user('thief', password='secret123')
        from .models import InventoryItem

        inv = InventoryItem.objects.create(
            user=User.objects.get(username='owner'), skin=Skin.objects.get(key='s0'))

        self.client.login(username='thief', password='secret123')
        res = self.client.post(reverse('cases:api_upgrade_roll'), {
            'case': self.case.id, 'ratio': '1', 'item': inv.id,
        })
        self.assertEqual(res.status_code, 400)
        inv.refresh_from_db()
        self.assertFalse(inv.consumed)
        self.assertFalse(InventoryItem.objects.filter(
            user__username='thief').exists())

    def test_upgrade_page_requires_login(self):
        res = self.client.get(reverse('cases:upgrade'))
        self.assertEqual(res.status_code, 302)
        self.assertIn('/auth/login/', res['Location'])

    def test_upgrade_result_rendered_once_then_cleared(self):
        User.objects.create_user('kelly', password='secret123')
        self.client.login(username='kelly', password='secret123')
        from .models import InventoryItem

        inv = InventoryItem.objects.create(
            user=User.objects.get(username='kelly'), skin=Skin.objects.get(key='s0'))

        self.client.post(reverse('cases:upgrade'), {
            'case': self.case.id, 'ratio': '1', 'item': inv.id,
        })
        first = self.client.get(reverse('cases:upgrade'))
        self.assertContains(first, 'upg-vs')
        second = self.client.get(reverse('cases:upgrade'))
        self.assertNotContains(second, 'upg-vs')

    def test_upgrade_roll_rejects_unsupported_ratio(self):
        User.objects.create_user('jack', password='secret123')
        self.client.login(username='jack', password='secret123')
        from .models import InventoryItem

        inv = InventoryItem.objects.create(
            user=User.objects.get(username='jack'), skin=Skin.objects.get(key='s0'))

        res = self.client.post(reverse('cases:api_upgrade_roll'), {
            'case': self.case.id, 'ratio': '2.75', 'item': inv.id,
        })
        self.assertEqual(res.status_code, 400)

    def test_upgrade_rejects_consumed_item(self):
        User.objects.create_user('gina', password='secret123')
        self.client.login(username='gina', password='secret123')
        from .models import InventoryItem

        inv = InventoryItem.objects.create(
            user=User.objects.get(username='gina'),
            skin=Skin.objects.get(key='s0'),
            consumed=True,
        )
        res = self.client.post(reverse('cases:api_upgrade_roll'), {
            'case': self.case.id, 'ratio': '1', 'item': inv.id,
        })
        self.assertEqual(res.status_code, 400)

    def test_upgrade_reused_item_rolls_twice(self):
        User.objects.create_user('hank', password='secret123')
        self.client.login(username='hank', password='secret123')
        from .models import InventoryItem

        inv = InventoryItem.objects.create(
            user=User.objects.get(username='hank'), skin=Skin.objects.get(key='s0'))

        payload = {'case': self.case.id, 'ratio': '1', 'item': inv.id}
        self.assertEqual(
            self.client.post(reverse('cases:api_upgrade_roll'), payload).status_code, 200)
        self.assertEqual(
            self.client.post(reverse('cases:api_upgrade_roll'), payload).status_code, 400)
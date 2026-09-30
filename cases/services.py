import random
from decimal import Decimal

from django.db import models, transaction

from .models import CaseItem, Drop, InventoryItem, Profile, Skin


def build_strip(case, size=64, winner=None):
    rows = list(case.items.select_related('skin'))
    if not rows:
        return []

    def as_item(row):
        return {'id': row.skin_id, 'name': row.skin.name,
                'image': row.skin.image_url, 'price': row.skin.price}

    if winner is None:
        return [as_item(random.choice(rows)) for _ in range(size)]

    pool = [r for r in rows if r.skin_id != winner.id] or rows
    win_row = next(r for r in rows if r.skin_id == winner.id)
    position = max(size - 25, 0)
    strip = [as_item(random.choice(pool)) for _ in range(size)]
    strip[position] = as_item(win_row)
    return strip


def _weighted_choice(qs):
    total = sum(r.weight for r in qs)
    if total <= 0:
        return random.choice(list(qs))
    pick = Decimal(str(random.random())) * total
    acc = Decimal('0')
    for row in qs:
        acc += row.weight
        if pick < acc:
            return row
    return qs[-1]


@transaction.atomic
def roll_case(case, user=None, profile=None):
    if profile is None and user is not None:
        profile = user.profile

    if profile is not None:
        profile = Profile.objects.select_for_update().get(pk=profile.pk)
        if profile.balance < case.price:
            raise ValueError('not_enough_balance')
        profile.balance -= case.price
        profile.wagered += case.price
        profile.save(update_fields=['balance', 'wagered'])

    rows = list(case.items.select_related('skin'))
    picked = _weighted_choice(rows)
    skin: Skin = picked.skin

    if user is not None:
        InventoryItem.objects.create(user=user, skin=skin)

    Drop.objects.create(
        user=user,
        username=user.username if user else 'бот',
        case=case,
        skin=skin,
        price=skin.price,
    )

    strip = build_strip(case, winner=skin)
    return {
        'skin': {
            'id': skin.id,
            'name': skin.name,
            'image': skin.image_url,
            'price': skin.price,
            'rarity': skin.rarity,
        },
        'strip': strip,
        'new_balance': profile.balance if profile else None,
    }


def upgrade_pool(case, from_price, ratio):
    threshold = from_price * ratio
    return threshold, list(
        case.items.select_related('skin').filter(skin__price__gte=threshold)
    )


def build_wheel(case, from_price, ratio):
    threshold, rows = upgrade_pool(case, from_price, ratio)
    if not rows:
        return {'segments': [], 'threshold': threshold, 'possible': False}

    total = float(sum(r.weight for r in rows))
    segments = [
        {
            'id': r.skin_id,
            'name': r.skin.name,
            'image': r.skin.image_url,
            'price': r.skin.price,
            'chance': float(r.weight) / total * 100,
        }
        for r in sorted(rows, key=lambda r: -r.skin.price)
    ]
    return {
        'segments': segments,
        'threshold': threshold,
        'possible': True,
    }


@transaction.atomic
def roll_upgrade(case, inv_item, ratio, user=None, profile=None):
    if profile is None and user is not None:
        profile = user.profile

    inv_item = InventoryItem.objects.select_for_update().select_related(
        'skin'
    ).get(pk=inv_item.pk)

    if inv_item.consumed or inv_item.user_id != (user.id if user else inv_item.user_id):
        raise ValueError('item_unavailable')

    from_price = inv_item.skin.price
    threshold, rows = upgrade_pool(case, from_price, ratio)
    if not rows:
        raise ValueError('empty_pool')

    picked = _weighted_choice(rows)
    skin: Skin = picked.skin

    InventoryItem.objects.filter(pk=inv_item.pk).update(consumed=True)

    if user is not None:
        InventoryItem.objects.create(user=user, skin=skin)

    Drop.objects.create(
        user=user,
        username=user.username if user else 'бот',
        case=case,
        skin=skin,
        price=skin.price,
    )

    if profile is not None:
        Profile.objects.filter(pk=profile.pk).update(
            wagered=models.F('wagered') + from_price
        )

    wheel = build_wheel(case, from_price, ratio)
    winner = next(s for s in wheel['segments'] if s['id'] == skin.id)

    return {
        'winner': winner,
        'wheel': wheel,
        'input': {'id': inv_item.skin_id, 'name': inv_item.skin.name,
                  'image': inv_item.skin.image_url, 'price': from_price},
        'spent': from_price,
        'ratio': ratio,
        'new_balance': profile.balance if profile else None,
    }
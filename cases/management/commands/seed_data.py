import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from cases.models import Case, CaseItem, Giveaway, Promo, Skin, Tournament

CASE_GROUPS = {
    'lonestar': ('main', False),
    'valkyra': ('main', False),
    'manticore': ('main', False),
    'neymar': ('football', False),
    'emerald': ('brand', False),
    'ak-47': ('weapon', False),
    'awp': ('weapon', False),
    'major2025': ('valve', False),
    'riptide': ('valve', False),
    'galerycase': ('valve', False),
    'berserk': ('fun', False),
    'agents': ('fun', False),
    'stickerssbox': ('fun', False),
    'bayonetknife': ('knife', False),
    'gloves': ('knife', False),
}

BONUS_CASES = [
    ('bonus-amber', 'Янтарный', 20, ['lonestar']),
    ('bonus-void', 'Пустота', 50, ['valkyra', 'neymar']),
    ('bonus-neon', 'Неоновый заряд', 100, ['berserk']),
]


WEIGHT_EXPONENT = 0.8
WEIGHT_FLOOR = 0.05


def weight_for(skin):
    p = max(skin.price, 1)
    return round(max(WEIGHT_FLOOR, 1000000 / (p ** WEIGHT_EXPONENT)), 6)


class Command(BaseCommand):
    help = 'Load skins/cases from case-battle-data.json and create demo content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=str(Path.cwd() / 'case-battle-data.json'),
            help='path to collected JSON dataset',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.exists():
            self.stderr.write(f'dataset not found: {path}')
            return

        data = json.loads(path.read_text(encoding='utf-8'))
        skins = {}
        for raw in data['skins']:
            name = raw['name'].replace('★', '').strip()
            weapon = (raw.get('weapon') or '').replace('★', '').strip()
            finish = (raw.get('skin') or '').replace('★', '').strip()
            skin, _ = Skin.objects.update_or_create(
                key=raw['id'],
                defaults={
                    'name': name,
                    'weapon': weapon,
                    'finish': finish,
                    'price': int(raw['price']),
                    'image_url': raw['image'],
                },
            )
            skins[raw['id']] = skin
        self.stdout.write(f'skins: {len(skins)}')

        for raw in data['cases']:
            group, is_bonus = CASE_GROUPS.get(raw['slug'], ('main', False))
            case, _ = Case.objects.update_or_create(
                slug=raw['slug'],
                defaults={
                    'name': raw['name'],
                    'price': int(raw['price']),
                    'image_back': raw.get('image_back', ''),
                    'image_front': raw.get('image_front', ''),
                    'group': group,
                    'is_bonus': is_bonus,
                },
            )
            case.items.all().delete()
            rows = [
                CaseItem(case=case, skin=skins[sid], weight=weight_for(skins[sid]))
                for sid in raw['skin_ids']
                if sid in skins
            ]
            CaseItem.objects.bulk_create(rows)

        for slug, name, price, sources in BONUS_CASES:
            donor = Case.objects.filter(slug=sources[0]).first()
            case, _ = Case.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'price': price,
                    'group': 'bonus',
                    'is_bonus': True,
                    'image_back': donor.image_back if donor else '',
                    'image_front': donor.image_front if donor else '',
                },
            )
            case.items.all().delete()
            pool = CaseItem.objects.filter(case__slug__in=sources).select_related('skin')
            picked = list(pool.order_by('?')[:30])
            CaseItem.objects.bulk_create([
                CaseItem(case=case, skin=r.skin, weight=r.weight) for r in picked
            ])

        self.stdout.write(f'cases: {Case.objects.count()}')

        for code, amount, percent, uses in [
            ('NEON-START', 5000, 0, 0),
            ('GLOW-10', 0, 10, 500),
            ('SHADOW-13', 0, 13, 300),
            ('CRATE-500', 500, 0, 1000),
            ('FREE-SPIN', 250, 0, 250),
        ]:
            Promo.objects.update_or_create(
                code=code,
                defaults={'amount': amount, 'percent': percent,
                          'max_uses': uses, 'is_active': True},
            )

        for title, prize, fee, pool in [
            ('Битва неона', 'AK-47 | Пустота', 100, 50000),
            ('Кубок люменов', '★ Нож Лунный свет', 250, 250000),
            ('Флуд-матч', 'AWP | Пепел', 50, 12000),
        ]:
            Tournament.objects.get_or_create(
                title=title,
                defaults={'prize_pool': pool, 'entry_fee': fee, 'max_players': 64},
            )

        if not Giveaway.objects.exists():
            top = Skin.objects.order_by('-price').first()
            giveaway = Giveaway.objects.create(
                title='Еженедельный розыгрыш NEON CRATE',
                prize='Лунный свет',
                prize_skin=top,
                entry_price=100,
            )
            giveaway.ends_at = None
            giveaway.save()
        self.stdout.write(self.style.SUCCESS('seed done'))
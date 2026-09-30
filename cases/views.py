import random
from datetime import timedelta

from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Case,
    CaseItem,
    Drop,
    Giveaway,
    GiveawayEntry,
    InventoryItem,
    Profile,
    Promo,
    PromoUse,
    Skin,
    Tournament,
)
from .services import build_wheel, roll_case, roll_upgrade

UPGRADE_RATIOS = [1, 1.5, 2, 3, 5]
UPGRADE_RATIO_CHOICES = [(str(r), '×%s' % r) for r in UPGRADE_RATIOS]

START_BALANCE = 10000
GROUPS = [
    ('main', 'Серийные кейсы'),
    ('football', 'Футбольная лига'),
    ('brand', 'Фирменные кейсы'),
    ('weapon', 'Кейсы оружия'),
    ('knife', 'Ножевые кейсы'),
    ('valve', 'Valve CS2'),
    ('fun', 'Тематические кейсы'),
]


def _profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def home(request):
    cases = Case.objects.all()
    q = request.GET.get('q', '').strip()
    if q:
        cases = cases.filter(name__icontains=q)

    sections = []
    for key, label in GROUPS:
        items = list(cases.filter(group=key))
        if items:
            sections.append({'key': key, 'label': label, 'cases': items})

    bonuses = list(cases.filter(is_bonus=True))
    drops = Drop.objects.select_related('skin', 'user')[:15]
    total = Drop.objects.count()

    return render(request, 'cases/home.html', {
        'sections': sections,
        'bonus_cases': bonuses,
        'drops': drops,
        'total_drops': total,
        'q': q,
        'player_count': 8123 + total,
    })


def case_detail(request, slug):
    case = get_object_or_404(Case, slug=slug)
    sort = request.GET.get('sort', 'default')
    items = case.items.select_related('skin')

    rows = list(items)
    if sort == 'asc':
        rows.sort(key=lambda r: r.skin.price)
    elif sort == 'desc':
        rows.sort(key=lambda r: r.skin.price, reverse=True)

    best = max(rows, key=lambda r: r.skin.price).skin if rows else None
    worst = min(rows, key=lambda r: r.skin.price).skin if rows else None

    total = float(sum(r.weight for r in rows)) or 1.0
    for r in rows:
        r.odds = round(100 * float(r.weight) / total, 2)

    return render(request, 'cases/case_detail.html', {
        'case': case,
        'rows': rows,
        'sort': sort,
        'best': best,
        'worst': worst,
    })


@require_POST
def api_open(request, slug):
    case = get_object_or_404(Case, slug=slug)
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=403)
    try:
        result = roll_case(case, request.user, _profile(request.user))
    except ValueError:
        return JsonResponse({'error': 'not_enough_balance'}, status=400)
    return JsonResponse(result)


def inventory(request):
    if not request.user.is_authenticated:
        return redirect('login')
    rows = request.user.inventory.filter(consumed=False).select_related('skin')
    total = sum(r.skin.price for r in rows)
    return render(request, 'cases/inventory.html', {
        'rows': rows,
        'total': total,
    })


def profile_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    p = _profile(request.user)
    drops = Drop.objects.filter(user=request.user)[:25]
    wins = Drop.objects.filter(user=request.user, price__gte=1000).count()
    return render(request, 'cases/profile.html', {
        'profile': p,
        'drops': drops,
        'wins': wins,
        'promos': Promo.objects.filter(is_active=True),
    })


def register(request):
    if request.user.is_authenticated:
        return redirect('cases:home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        if not username or len(password) < 6:
            return render(request, 'registration/register.html',
                          {'error': 'Логин и пароль от 6 символов.'})
        if User.objects.filter(username__iexact=username).exists():
            return render(request, 'registration/register.html',
                          {'error': 'Такой логин уже занят.'})
        user = User.objects.create_user(username=username, password=password)
        _profile(user)
        login(request, user)
        return redirect('cases:home')
    return render(request, 'registration/register.html')


def top_drops(request):
    rows = Drop.objects.select_related('skin', 'case').order_by('-price')[:50]
    return render(request, 'cases/top_drops.html', {'rows': rows})


def _upgrade_page(request, preview=None, error=None, result=None):
    own = request.user.inventory.filter(consumed=False).select_related('skin')
    return render(request, 'cases/upgrade.html', {
        'cases': Case.objects.all(),
        'own': own,
        'ratios': UPGRADE_RATIO_CHOICES,
        'preview': preview,
        'error': error,
        'result': result,
    })


def upgrade(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method != 'POST':
        return _upgrade_page(request, result=request.session.pop('last_upgrade', None))

    try:
        case, ratio, inv = _upgrade_inputs(request)
        result = roll_upgrade(case, inv, ratio, request.user)
    except ValueError as exc:
        return _upgrade_page(request, error=_upgrade_error(exc))

    request.session['last_upgrade'] = result
    return redirect('cases:upgrade')


def _upgrade_error(exc):
    return {
        'item_unavailable': 'Предмет уже использован.',
        'empty_pool': 'В этом кейсе нет предметов подходящей цены.',
        'no_case': 'Выберите кейс.',
        'bad_ratio': 'Недоступный коэффициент.',
    }.get(str(exc), 'Не удалось выполнить апгрейд.')


def _upgrade_inputs(request):
    case = Case.objects.filter(pk=request.POST.get('case')).first()
    if not case:
        raise ValueError('no_case')

    try:
        ratio = float(request.POST.get('ratio') or 1)
    except (TypeError, ValueError):
        raise ValueError('bad_ratio')
    if ratio not in UPGRADE_RATIOS:
        raise ValueError('bad_ratio')

    inv = request.user.inventory.filter(
        consumed=False, pk=request.POST.get('item')
    ).select_related('skin').first()
    if not inv:
        raise ValueError('item_unavailable')

    return case, ratio, inv


@require_POST
def api_upgrade_preview(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=403)

    try:
        case, ratio, inv = _upgrade_inputs(request)
    except ValueError as exc:
        return JsonResponse({'error': _upgrade_error(exc)}, status=400)

    wheel = build_wheel(case, inv.skin.price, ratio)
    wheel['input'] = {'id': inv.skin.id, 'name': inv.skin.name,
                      'image': inv.skin.image_url, 'price': inv.skin.price}
    return JsonResponse(wheel)


@require_POST
def api_upgrade_roll(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=403)

    try:
        case, ratio, inv = _upgrade_inputs(request)
        result = roll_upgrade(case, inv, ratio, request.user)
    except ValueError as exc:
        return JsonResponse({'error': _upgrade_error(exc)}, status=400)

    request.session['last_upgrade'] = result
    return JsonResponse(result)


def contract(request):
    if not request.user.is_authenticated:
        return redirect('login')
    cases = Case.objects.all()
    result = None
    error = None
    if request.method == 'POST':
        case = get_object_or_404(Case, pk=request.POST.get('case'))
        ids = request.POST.getlist('items')
        if len(ids) != 3:
            error = 'Нужно выбрать ровно 3 предмета.'
        else:
            own = request.user.inventory.filter(consumed=False, id__in=ids)
            if len(own) != 3:
                error = 'Один из предметов уже использован.'
            else:
                profile = Profile.objects.select_for_update().get(pk=request.user.profile.pk)
                out = roll_case(case, request.user, profile)
                own.update(consumed=True)
                result = out['skin']
    return render(request, 'cases/contract.html', {
        'cases': cases,
        'result': result,
        'error': error,
        'own': request.user.inventory.filter(consumed=False).select_related('skin'),
    })


def giveaways(request):
    rows = Giveaway.objects.all()
    return render(request, 'cases/giveaways.html', {'giveaways': rows})


@require_POST
def giveaway_enter(request, pk):
    g = get_object_or_404(Giveaway, pk=pk)
    if not request.user.is_authenticated:
        return redirect('login')
    if g.is_finished:
        return redirect('cases:giveaways')
    profile = Profile.objects.select_for_update().get(pk=request.user.profile.pk)
    if profile.balance < g.entry_price:
        GiveawayEntry.objects.filter(giveaway=g, user=request.user).delete()
        return redirect('cases:giveaways')
    profile.balance -= g.entry_price
    profile.save(update_fields=['balance'])
    GiveawayEntry.objects.get_or_create(giveaway=g, user=request.user)
    return redirect('cases:giveaways')


@require_POST
@transaction.atomic
def giveaway_pick(request, pk):
    g = get_object_or_404(Giveaway, pk=pk)
    if not request.user.is_staff:
        return redirect('cases:giveaways')
    entries = list(g.entries.select_related('user'))
    if not entries:
        g.winner = request.user
        g.winner_name = request.user.username
    else:
        win = random.choice(entries)
        g.winner = win.user
        g.winner_name = win.user.username
        g.prize_skin = None
    g.save()
    return redirect('cases:giveaways')


def tournaments(request):
    return render(request, 'cases/tournaments.html',
                  {'tournaments': Tournament.objects.all()})


@require_POST
def promo_redeem(request):
    if not request.user.is_authenticated:
        return redirect('login')
    code = request.POST.get('code', '').strip().upper()
    profile = _profile(request.user)
    promo = Promo.objects.filter(code=code, is_active=True).first()
    if not promo:
        messages = 'Промокод не найден.'
    elif promo.is_exhausted:
        messages = 'Промокод больше не действует.'
    elif PromoUse.objects.filter(promo=promo, user=request.user).exists():
        messages = 'Вы уже использовали этот промокод.'
    else:
        value = promo.amount
        if promo.percent:
            value = max(value, int(profile.balance * promo.percent / 100))
        profile.balance += value
        profile.save(update_fields=['balance'])
        PromoUse.objects.create(promo=promo, user=request.user)
        Promo.objects.filter(pk=promo.pk).update(used_count=F('used_count') + 1)
        messages = f'Начислено {value} NEON'
    from django.contrib import messages as dj_messages
    dj_messages.success(request, messages)
    return redirect(request.POST.get('next') or 'cases:profile')


def faq(request):
    return render(request, 'cases/faq.html')


def rule(request, kind):
    titles = {
        'terms': 'Пользовательское соглашение',
        'aml': 'AML политика',
        'security': 'Политика безопасности',
    }
    return render(request, 'cases/rule.html', {'title': titles.get(kind, 'Документ'), 'kind': kind})


def support(request):
    return render(request, 'cases/support.html')
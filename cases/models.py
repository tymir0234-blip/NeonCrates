from django.contrib.auth.models import User
from django.db import models


class Rarity(models.TextChoices):
    CONSUMER = 'consumer', 'Обычный'
    INDUSTRIAL = 'industrial', 'Промышленный'
    MILITARY = 'military', 'Армейский'
    RESTRICTED = 'restricted', 'Ограниченный'
    CLASSIFIED = 'classified', 'Засекреченный'
    COVERT = 'covert', 'Тайный'
    CONTAINER = 'container', 'Контейнер'


RARITY_ORDER = [r.value for r in Rarity]


class Skin(models.Model):
    key = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=160)
    weapon = models.CharField(max_length=100, blank=True)
    finish = models.CharField(max_length=100, blank=True)
    price = models.PositiveIntegerField(default=0)
    image_url = models.URLField(max_length=400)

    class Meta:
        ordering = ['price', 'name']
        indexes = [models.Index(fields=['price'])]

    def __str__(self):
        return self.name

    RARITY_THRESHOLDS = [
        (30000, Rarity.COVERT),
        (8000, Rarity.CLASSIFIED),
        (2000, Rarity.RESTRICTED),
        (600, Rarity.MILITARY),
        (200, Rarity.INDUSTRIAL),
    ]

    @property
    def rarity(self):
        for threshold, label in self.RARITY_THRESHOLDS:
            if self.price >= threshold:
                return label
        return Rarity.CONSUMER


class Case(models.Model):
    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=100)
    price = models.PositiveIntegerField(default=0)
    image_back = models.URLField(max_length=400, blank=True)
    image_front = models.URLField(max_length=400, blank=True)
    group = models.CharField(max_length=64, default='main', db_index=True)
    is_bonus = models.BooleanField(default=False)

    class Meta:
        ordering = ['price', 'name']

    def __str__(self):
        return self.name

    @property
    def is_limited(self):
        return self.group == 'limited'


class CaseItem(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='items')
    skin = models.ForeignKey(Skin, on_delete=models.CASCADE)
    weight = models.DecimalField(max_digits=12, decimal_places=6, default=1)

    class Meta:
        unique_together = ('case', 'skin')
        indexes = [models.Index(fields=['case'])]


class Promo(models.Model):
    code = models.CharField(max_length=40, unique=True)
    amount = models.PositiveIntegerField(default=0)
    percent = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    max_uses = models.PositiveIntegerField(default=0)
    used_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    @property
    def is_exhausted(self):
        return self.max_uses > 0 and self.used_count >= self.max_uses


class PromoUse(models.Model):
    promo = models.ForeignKey(Promo, on_delete=models.CASCADE, related_name='uses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('promo', 'user')


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    balance = models.IntegerField(default=0)
    wagered = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} · {self.balance}'


class InventoryItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inventory')
    skin = models.ForeignKey(Skin, on_delete=models.CASCADE)
    acquired_at = models.DateTimeField(auto_now_add=True)
    consumed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-acquired_at']


class Drop(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(max_length=150, default='')
    case = models.ForeignKey(Case, on_delete=models.SET_NULL, null=True, blank=True)
    skin = models.ForeignKey(Skin, on_delete=models.CASCADE)
    price = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['-created_at']), models.Index(fields=['-price'])]


class Giveaway(models.Model):
    title = models.CharField(max_length=160)
    prize = models.CharField(max_length=160)
    prize_skin = models.ForeignKey(
        Skin, on_delete=models.SET_NULL, null=True, blank=True
    )
    entry_price = models.PositiveIntegerField(default=0)
    winner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='giveaway_wins'
    )
    winner_name = models.CharField(max_length=150, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_finished(self):
        return self.winner_id is not None


class GiveawayEntry(models.Model):
    giveaway = models.ForeignKey(Giveaway, on_delete=models.CASCADE, related_name='entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('giveaway', 'user')


class Tournament(models.Model):
    title = models.CharField(max_length=160)
    prize_pool = models.PositiveIntegerField(default=0)
    entry_fee = models.PositiveIntegerField(default=0)
    max_players = models.PositiveIntegerField(default=64)
    starts_at = models.DateTimeField(null=True, blank=True)
    is_open = models.BooleanField(default=True)

    class Meta:
        ordering = ['starts_at', 'title']

    def __str__(self):
        return self.title
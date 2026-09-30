from django.contrib import admin

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


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price', 'group', 'is_bonus']
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ['group', 'is_bonus']


class RarityFilter(admin.SimpleListFilter):
    title = 'редкость'
    parameter_name = 'rarity'

    def lookups(self, request, model_admin):
        from .models import Rarity
        return [(r.value, r.label) for r in Rarity]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        qs = queryset
        for threshold, label in Skin.RARITY_THRESHOLDS:
            if value == label:
                lo = threshold
                hi = next((t for t, _ in Skin.RARITY_THRESHOLDS if t > threshold), None)
                return qs.filter(price__gte=lo) if hi is None else qs.filter(price__gte=lo, price__lt=hi)
        return qs.filter(price__lt=200)


@admin.register(Skin)
class SkinAdmin(admin.ModelAdmin):
    list_display = ['name', 'weapon', 'price', 'rarity']
    search_fields = ['name', 'weapon', 'key']
    list_filter = [RarityFilter]


@admin.register(CaseItem)
class CaseItemAdmin(admin.ModelAdmin):
    list_display = ['case', 'skin', 'weight']
    list_filter = ['case']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'wagered', 'created_at']
    search_fields = ['user__username']


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'skin', 'acquired_at', 'consumed']
    list_filter = ['consumed']


@admin.register(Drop)
class DropAdmin(admin.ModelAdmin):
    list_display = ['username', 'skin', 'case', 'price', 'created_at']
    search_fields = ['username', 'skin__name']


@admin.register(Promo)
class PromoAdmin(admin.ModelAdmin):
    list_display = ['code', 'amount', 'percent', 'is_active', 'used_count', 'max_uses']


@admin.register(PromoUse)
class PromoUseAdmin(admin.ModelAdmin):
    list_display = ['promo', 'user', 'created_at']


@admin.register(Giveaway)
class GiveawayAdmin(admin.ModelAdmin):
    list_display = ['title', 'prize', 'entry_price', 'winner_name', 'created_at']


@admin.register(GiveawayEntry)
class GiveawayEntryAdmin(admin.ModelAdmin):
    list_display = ['giveaway', 'user', 'created_at']


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['title', 'prize_pool', 'entry_fee', 'is_open', 'starts_at']
from django.contrib import admin

from profiles.models import Follow, Profile, ProjectEntry


class ProjectEntryInline(admin.TabularInline):
    model = ProjectEntry
    extra = 0
    readonly_fields = ['added_at', 'display_order']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['slug', 'display_name', 'user', 'status', 'follower_count', 'following_count', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['slug', 'display_name', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'follower_count', 'following_count']
    inlines = [ProjectEntryInline]


@admin.register(ProjectEntry)
class ProjectEntryAdmin(admin.ModelAdmin):
    list_display = ['profile', 'repository', 'display_order', 'added_at']
    list_filter = ['added_at']
    search_fields = ['profile__slug', 'repository__name']
    readonly_fields = ['added_at']


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ['follower', 'target', 'created_at']
    list_filter = ['created_at']
    search_fields = ['follower__slug', 'target__slug']
    readonly_fields = ['created_at']

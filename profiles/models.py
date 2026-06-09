from django.conf import settings
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models


class Profile(models.Model):
    """Developer profile — user-controlled professional identity."""

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    slug = models.SlugField(
        max_length=40,
        unique=True,
        validators=[
            MinLengthValidator(3),
            RegexValidator(
                regex=r'^[a-z][a-z0-9\-]*$',
                message='Slug must start with a letter and contain only lowercase letters, numbers, and hyphens.',
            ),
        ],
    )
    display_name = models.CharField(max_length=100)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)
    bio = models.TextField(max_length=500, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    website_url = models.URLField(max_length=200, null=True, blank=True)
    github_username = models.CharField(max_length=39, null=True, blank=True)  # GitHub max is 39

    skill_tags = models.JSONField(default=list)  # List of strings, max 20 items

    follower_count = models.IntegerField(default=0)
    following_count = models.IntegerField(default=0)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    github_sync_status = models.CharField(max_length=20, null=True, blank=True)  # 'never', 'synced', 'failed'

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'profiles_profile'
        indexes = [
            models.Index(fields=['slug'], name='profile_slug_idx'),
            models.Index(fields=['status'], name='profile_status_idx'),
        ]

    def __str__(self):
        return f"{self.display_name} (@{self.slug})"


class ProjectEntry(models.Model):
    """Link between a profile and a repository for project showcase."""

    profile = models.ForeignKey(
        'profiles.Profile',
        on_delete=models.CASCADE,
        related_name='projects',
    )
    repository = models.ForeignKey(
        'explorer.Repository',
        on_delete=models.CASCADE,
        related_name='profile_entries',
    )
    custom_description = models.CharField(max_length=300, null=True, blank=True)
    display_order = models.IntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'profiles_projectentry'
        ordering = ['display_order', '-added_at']
        constraints = [
            models.UniqueConstraint(
                fields=['profile', 'repository'],
                name='unique_profile_repository',
            ),
        ]
        indexes = [
            models.Index(
                fields=['profile', 'display_order'],
                name='project_profile_order_idx',
            ),
        ]

    def __str__(self):
        return f"{self.profile.slug} - {self.repository.name}"


class Follow(models.Model):
    """Follow relationship between profiles."""

    follower = models.ForeignKey(
        'profiles.Profile',
        on_delete=models.CASCADE,
        related_name='following_set',
    )
    target = models.ForeignKey(
        'profiles.Profile',
        on_delete=models.CASCADE,
        related_name='follower_set',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'profiles_follow'
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'target'],
                name='unique_follow_relationship',
            ),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F('target')),
                name='no_self_follow',
            ),
        ]
        indexes = [
            models.Index(fields=['follower', '-created_at'], name='follow_follower_idx'),
            models.Index(fields=['target', '-created_at'], name='follow_target_idx'),
        ]

    def __str__(self):
        return f"{self.follower.slug} \u2192 {self.target.slug}"

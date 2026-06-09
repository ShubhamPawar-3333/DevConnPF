"""
Task 13.1 — Unit tests for Profile, ProjectEntry, and Follow model constraints.
"""

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from explorer.models import Repository
from profiles.models import Follow, Profile, ProjectEntry

User = get_user_model()


def make_user(username, email=None):
    return User.objects.create_user(
        username=username,
        email=email or f"{username}@example.com",
        password="pass",
    )


class TestProfileModelConstraints(TestCase):
    """Profile model constraints and defaults."""

    def test_slug_uniqueness_enforced_at_db_level(self):
        u1 = make_user("p-u1")
        u2 = make_user("p-u2")
        Profile.objects.create(user=u1, slug="same-slug", display_name="One")
        with self.assertRaises(IntegrityError):
            Profile.objects.create(user=u2, slug="same-slug", display_name="Two")

    def test_one_to_one_user_enforced(self):
        u = make_user("p-u3")
        Profile.objects.create(user=u, slug="p-u3-slug", display_name="Dev")
        with self.assertRaises(IntegrityError):
            Profile.objects.create(user=u, slug="p-u3-slug-2", display_name="Dev2")

    def test_default_status_is_active(self):
        u = make_user("p-u4")
        p = Profile.objects.create(user=u, slug="p-u4-slug", display_name="Dev")
        self.assertEqual(p.status, "active")

    def test_default_follower_count_is_zero(self):
        u = make_user("p-u5")
        p = Profile.objects.create(user=u, slug="p-u5-slug", display_name="Dev")
        self.assertEqual(p.follower_count, 0)

    def test_default_skill_tags_is_empty_list(self):
        u = make_user("p-u6")
        p = Profile.objects.create(user=u, slug="p-u6-slug", display_name="Dev")
        self.assertEqual(p.skill_tags, [])


class TestProjectEntryConstraints(TestCase):
    """ProjectEntry unique constraint on (profile, repository)."""

    def setUp(self):
        self.user = make_user("pe-user")
        self.profile = Profile.objects.create(user=self.user, slug="pe-dev", display_name="PE Dev")
        self.repo = Repository.objects.create(user=self.user, name="pe-repo", status="ready")

    def test_unique_profile_repository_enforced(self):
        ProjectEntry.objects.create(profile=self.profile, repository=self.repo, display_order=0)
        with self.assertRaises(IntegrityError):
            ProjectEntry.objects.create(profile=self.profile, repository=self.repo, display_order=1)


class TestFollowConstraints(TestCase):
    """Follow model: unique constraint and self-follow check at DB level."""

    def setUp(self):
        self.u1 = make_user("fw-u1")
        self.u2 = make_user("fw-u2")
        self.p1 = Profile.objects.create(user=self.u1, slug="fw-p1", display_name="P1")
        self.p2 = Profile.objects.create(user=self.u2, slug="fw-p2", display_name="P2")

    def test_unique_follow_enforced(self):
        Follow.objects.create(follower=self.p1, target=self.p2)
        with self.assertRaises(IntegrityError):
            Follow.objects.create(follower=self.p1, target=self.p2)

    def test_self_follow_prevented_at_db_level(self):
        with self.assertRaises(IntegrityError):
            Follow.objects.create(follower=self.p1, target=self.p1)

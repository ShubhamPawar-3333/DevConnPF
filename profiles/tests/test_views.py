"""
Task 13.3 — Integration tests for API views: smoke tests, edge cases.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from profiles.models import Follow, Profile
from profiles.services import ProfileService

User = get_user_model()


def make_user(username, email=None):
    return User.objects.create_user(
        username=username,
        email=email or f"{username}@example.com",
        password="pass",
    )


def make_profile(user, slug, display_name="Dev"):
    return Profile.objects.create(user=user, slug=slug, display_name=display_name)


class TestProfileURLRouting(TestCase):
    """Smoke tests — URL routes are registered correctly."""

    def test_profile_url_resolves(self):
        u = make_user("url-u1")
        make_profile(u, "url-u1")
        resp = self.client.get("/api/profiles/url-u1/")
        self.assertEqual(resp.status_code, 200)

    def test_search_url_resolves(self):
        resp = self.client.get("/api/profiles/search/?q=test")
        self.assertEqual(resp.status_code, 200)

    def test_me_get_requires_auth(self):
        resp = self.client.get("/api/profiles/me/")
        self.assertIn(resp.status_code, [401, 403])

    def test_anonymous_profile_access_returns_200(self):
        u = make_user("anon-u1")
        make_profile(u, "anon-u1")
        resp = self.client.get("/api/profiles/anon-u1/")
        self.assertEqual(resp.status_code, 200)


class TestProfileCreationEdgeCases(TestCase):
    """Profile creation edge cases."""

    def setUp(self):
        self.user = make_user("ce-user")
        self.client = Client()
        self.client.force_login(self.user)

    def test_missing_display_name_returns_400(self):
        resp = self.client.post(
            "/api/profiles/me/",
            {"slug": "valid-slug"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("display_name", resp.json().get("fields", {}))

    def test_missing_slug_returns_400(self):
        resp = self.client.post(
            "/api/profiles/me/",
            {"display_name": "Test Dev"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_profile_returns_400(self):
        make_profile(self.user, "ce-slug")
        resp = self.client.post(
            "/api/profiles/me/",
            {"display_name": "Test", "slug": "ce-slug2"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class TestProfileViewEdgeCases(TestCase):
    """Profile view edge cases."""

    def test_nonexistent_slug_returns_404(self):
        resp = self.client.get("/api/profiles/does-not-exist/")
        self.assertEqual(resp.status_code, 404)

    def test_inactive_slug_returns_404(self):
        u = make_user("inactive-u")
        p = make_profile(u, "inactive-p")
        p.status = "inactive"
        p.save()
        resp = self.client.get("/api/profiles/inactive-p/")
        self.assertEqual(resp.status_code, 404)


class TestSearchEdgeCases(TestCase):
    """Search endpoint edge cases."""

    def test_empty_query_returns_400(self):
        resp = self.client.get("/api/profiles/search/")
        self.assertEqual(resp.status_code, 400)

    def test_no_matches_returns_empty_list_with_zero_count(self):
        resp = self.client.get("/api/profiles/search/?q=zzznomatch")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    def test_query_over_200_chars_returns_400(self):
        resp = self.client.get(f"/api/profiles/search/?q={'a' * 201}")
        self.assertEqual(resp.status_code, 400)


class TestFollowEdgeCases(TestCase):
    """Follow endpoint edge cases."""

    def setUp(self):
        self.u1 = make_user("fw-ev-u1")
        self.u2 = make_user("fw-ev-u2")
        self.p1 = make_profile(self.u1, "fw-ev-p1")
        self.p2 = make_profile(self.u2, "fw-ev-p2")
        self.client = Client()
        self.client.force_login(self.u1)

    def test_unfollow_when_not_following_returns_404(self):
        resp = self.client.delete(f"/api/profiles/{self.p2.slug}/unfollow/")
        self.assertEqual(resp.status_code, 404)

    def test_reserved_slug_list_contains_required_entries(self):
        required = {"admin", "api", "auth", "settings", "dashboard",
                    "login", "explore", "shared", "repos", "search"}
        self.assertTrue(required.issubset(ProfileService.RESERVED_SLUGS))

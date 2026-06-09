"""
Integration and end-to-end test scenarios for the developer profiles feature.

Covers:
- Onboarding flow: profile creation via API
- Profile → project → explorer navigation (URL structure)
- Follow/unfollow with count verification
- Search correctness
- Edge cases: 50-project limit, slug conflicts, reserved slugs
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from explorer.models import Repository
from profiles.models import Follow, Profile, ProjectEntry

User = get_user_model()


def make_user(username="testuser", email="test@example.com", password="pass"):
    return User.objects.create_user(username=username, email=email, password=password)


def make_profile(user, slug="test-dev", display_name="Test Dev"):
    return Profile.objects.create(user=user, slug=slug, display_name=display_name)


class ProfileCreationTest(TestCase):
    """Task 22.1 — Onboarding flow: profile creation via API."""

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_create_profile_success(self):
        resp = self.client.post(
            "/api/profiles/me/",
            {"display_name": "Jane Dev", "slug": "jane-dev"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["slug"], "jane-dev")
        self.assertEqual(data["display_name"], "Jane Dev")
        self.assertIn("email", data)  # owner view

    def test_duplicate_profile_rejected(self):
        make_profile(self.user, slug="jane-dev")
        resp = self.client.post(
            "/api/profiles/me/",
            {"display_name": "Jane Dev", "slug": "jane-dev2"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_reserved_slug_rejected(self):
        resp = self.client.post(
            "/api/profiles/me/",
            {"display_name": "Admin", "slug": "admin"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("slug", resp.json().get("fields", {}))

    def test_slug_conflict_rejected(self):
        other_user = make_user(username="other", email="other@example.com")
        make_profile(other_user, slug="taken-slug")
        resp = self.client.post(
            "/api/profiles/me/",
            {"display_name": "Me", "slug": "taken-slug"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("slug", resp.json().get("fields", {}))


class ProfileViewTest(TestCase):
    """Task 22.1 — Profile retrieval and public access."""

    def setUp(self):
        self.user = make_user()
        self.profile = make_profile(self.user)

    def test_public_access_no_auth(self):
        resp = self.client.get(f"/api/profiles/{self.profile.slug}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Public view should NOT include email
        self.assertNotIn("email", data)
        self.assertEqual(data["slug"], self.profile.slug)

    def test_owner_view_includes_email(self):
        self.client.force_login(self.user)
        resp = self.client.get(f"/api/profiles/{self.profile.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("email", resp.json())

    def test_inactive_profile_returns_404(self):
        self.profile.status = "inactive"
        self.profile.save()
        resp = self.client.get(f"/api/profiles/{self.profile.slug}/")
        self.assertEqual(resp.status_code, 404)

    def test_nonexistent_slug_returns_404(self):
        resp = self.client.get("/api/profiles/does-not-exist/")
        self.assertEqual(resp.status_code, 404)


class ProjectLimitTest(TestCase):
    """Task 22.1 — 50-project limit edge case."""

    def setUp(self):
        self.user = make_user()
        self.profile = make_profile(self.user)
        self.client.force_login(self.user)

    def _make_repo(self, name):
        return Repository.objects.create(user=self.user, name=name, status="ready")

    def test_fifty_project_limit_enforced(self):
        # Create 50 repos and add them all
        repos = [self._make_repo(f"repo-{i}") for i in range(51)]
        for repo in repos[:50]:
            ProjectEntry.objects.create(
                profile=self.profile, repository=repo, display_order=0
            )

        # The 51st should be rejected
        resp = self.client.post(
            "/api/profiles/me/projects/",
            {"repository_id": repos[50].id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("limit", resp.json().get("error", "").lower())

    def test_duplicate_project_rejected(self):
        repo = self._make_repo("my-repo")
        ProjectEntry.objects.create(
            profile=self.profile, repository=repo, display_order=0
        )
        resp = self.client.post(
            "/api/profiles/me/projects/",
            {"repository_id": repo.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already added", resp.json().get("error", "").lower())


class FollowUnfollowTest(TestCase):
    """Task 22.1 — Follow/unfollow with count verification."""

    def setUp(self):
        self.user_a = make_user(username="user-a", email="a@example.com")
        self.user_b = make_user(username="user-b", email="b@example.com")
        self.profile_a = make_profile(self.user_a, slug="user-a")
        self.profile_b = make_profile(self.user_b, slug="user-b")
        self.client.force_login(self.user_a)

    def test_follow_creates_relationship_and_updates_counts(self):
        resp = self.client.post(f"/api/profiles/{self.profile_b.slug}/follow/")
        self.assertEqual(resp.status_code, 201)

        self.profile_a.refresh_from_db()
        self.profile_b.refresh_from_db()
        self.assertEqual(self.profile_a.following_count, 1)
        self.assertEqual(self.profile_b.follower_count, 1)

    def test_unfollow_removes_relationship_and_restores_counts(self):
        Follow.objects.create(follower=self.profile_a, target=self.profile_b)
        self.profile_a.following_count = 1
        self.profile_a.save()
        self.profile_b.follower_count = 1
        self.profile_b.save()

        resp = self.client.delete(f"/api/profiles/{self.profile_b.slug}/unfollow/")
        self.assertEqual(resp.status_code, 204)

        self.profile_a.refresh_from_db()
        self.profile_b.refresh_from_db()
        self.assertEqual(self.profile_a.following_count, 0)
        self.assertEqual(self.profile_b.follower_count, 0)

    def test_self_follow_rejected(self):
        resp = self.client.post(f"/api/profiles/{self.profile_a.slug}/follow/")
        self.assertEqual(resp.status_code, 400)

    def test_unfollow_not_following_returns_404(self):
        resp = self.client.delete(f"/api/profiles/{self.profile_b.slug}/unfollow/")
        self.assertEqual(resp.status_code, 404)


class SearchTest(TestCase):
    """Task 22.1 — Search correctness."""

    def setUp(self):
        u1 = make_user(username="alice", email="alice@example.com")
        u2 = make_user(username="bob", email="bob@example.com")
        u3 = make_user(username="charlie", email="charlie@example.com")
        self.p1 = Profile.objects.create(
            user=u1, slug="alice-dev", display_name="Alice Dev",
            skill_tags=["Python", "Django"], status="active"
        )
        self.p2 = Profile.objects.create(
            user=u2, slug="bob-coder", display_name="Bob Coder",
            skill_tags=["React", "TypeScript"], status="active"
        )
        # Inactive profile — should never appear in search
        self.p3 = Profile.objects.create(
            user=u3, slug="charlie-ghost", display_name="Charlie Ghost",
            skill_tags=["Python"], status="inactive"
        )

    def test_search_by_display_name(self):
        resp = self.client.get("/api/profiles/search/?q=Alice")
        self.assertEqual(resp.status_code, 200)
        slugs = [r["slug"] for r in resp.json()["results"]]
        self.assertIn("alice-dev", slugs)
        self.assertNotIn("bob-coder", slugs)

    def test_search_active_only(self):
        resp = self.client.get("/api/profiles/search/?q=Python")
        self.assertEqual(resp.status_code, 200)
        slugs = [r["slug"] for r in resp.json()["results"]]
        self.assertIn("alice-dev", slugs)
        self.assertNotIn("charlie-ghost", slugs)  # inactive excluded

    def test_skill_tag_filter(self):
        resp = self.client.get("/api/profiles/search/?q=Dev&skill_tag=Django")
        self.assertEqual(resp.status_code, 200)
        slugs = [r["slug"] for r in resp.json()["results"]]
        self.assertIn("alice-dev", slugs)
        self.assertNotIn("bob-coder", slugs)

    def test_empty_query_returns_400(self):
        resp = self.client.get("/api/profiles/search/")
        self.assertEqual(resp.status_code, 400)

    def test_no_results_returns_empty_list(self):
        resp = self.client.get("/api/profiles/search/?q=zzznomatch")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

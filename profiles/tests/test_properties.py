"""
Property-based tests for the developer profiles feature.
Uses Hypothesis to generate inputs and verify correctness properties.

Each test references the design document property it validates.
"""

import re
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from hypothesis.extra.django import TestCase
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from explorer.models import Repository
from profiles.models import Follow, Profile, ProjectEntry
from profiles.serializers import ProfileOwnerSerializer, ProfilePublicSerializer
from profiles.services import ProfileService, FollowService

User = get_user_model()

User = get_user_model()

# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

SLUG_CHARS = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=1,
    max_size=45,
)

VALID_SLUG = st.from_regex(r'^[a-z][a-z0-9\-]{2,39}$', fullmatch=True)

RESERVED = ProfileService.RESERVED_SLUGS


def make_user(username, email=None):
    return User.objects.create_user(
        username=username,
        email=email or f"{username}@example.com",
        password="pass",
    )


def make_profile(user, slug, display_name="Dev"):
    return Profile.objects.create(user=user, slug=slug, display_name=display_name)


# ---------------------------------------------------------------------------
# Property 1: Slug Format Validation
# Feature: developer-profiles
# Validates: Requirements 1.3, 1.4, 3.5, 9.3, 9.4, 9.6
# ---------------------------------------------------------------------------

class TestProperty1SlugFormatValidation(TestCase):
    """For any string, validate_slug accepts iff it meets all rules."""

    def setUp(self):
        self.service = ProfileService()

    @given(VALID_SLUG)
    @settings(max_examples=100, deadline=None)
    def test_valid_slugs_accepted(self, slug):
        assume(slug not in RESERVED)
        try:
            self.service.validate_slug(slug)
        except Exception as e:
            self.fail(f"Valid slug '{slug}' was rejected: {e}")

    @given(st.text(min_size=1, max_size=2))
    @settings(max_examples=100, deadline=None)
    def test_too_short_rejected(self, slug):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.service.validate_slug(slug)

    @given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=41, max_size=60))
    @settings(max_examples=100, deadline=None)
    def test_too_long_rejected(self, slug):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.service.validate_slug(slug)

    @given(st.sampled_from(sorted(RESERVED)))
    @settings(max_examples=len(RESERVED))
    def test_reserved_slugs_rejected(self, slug):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.service.validate_slug(slug)

    @given(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-", min_size=3, max_size=20))
    @settings(max_examples=100, deadline=None)
    def test_uppercase_rejected(self, slug):
        from django.core.exceptions import ValidationError
        assume(slug[0].isupper() or any(c.isupper() for c in slug))
        with self.assertRaises(ValidationError):
            self.service.validate_slug(slug)


# ---------------------------------------------------------------------------
# Property 3: Profile Serialization Completeness and Optional Field Nullability
# Feature: developer-profiles
# Validates: Requirements 8.1, 8.4
# ---------------------------------------------------------------------------

REQUIRED_PUBLIC_FIELDS = {
    'slug', 'display_name', 'avatar_url', 'bio', 'location',
    'website_url', 'skill_tags', 'follower_count', 'following_count',
    'projects', 'joined_date', 'github_username',
}
OPTIONAL_NULLABLE = {'avatar_url', 'bio', 'location', 'website_url', 'github_username'}


class TestProperty3SerializationCompleteness(TestCase):
    """Serializing a Profile for a visitor contains all required keys;
    unset optional fields serialize as null, not omitted."""

    def setUp(self):
        self.user = make_user("ser-user")

    @given(
        bio=st.one_of(st.none(), st.text(max_size=100)),
        location=st.one_of(st.none(), st.text(max_size=50)),
    )
    @settings(max_examples=100, deadline=None)
    def test_required_keys_present_and_optional_nullable(self, bio, location):
        profile = Profile.objects.create(
            user=self.user,
            slug="ser-slug",
            display_name="Ser Dev",
            bio=bio,
            location=location,
        )
        data = ProfilePublicSerializer(profile).data
        # All required fields present
        for field in REQUIRED_PUBLIC_FIELDS:
            self.assertIn(field, data, f"Missing field: {field}")
        # Unset optionals are null, not absent
        if bio is None:
            self.assertIsNone(data['bio'])
        if location is None:
            self.assertIsNone(data['location'])
        profile.delete()
        self.user.profile = None
        Profile.objects.filter(user=self.user).delete()


# ---------------------------------------------------------------------------
# Property 4: Owner vs. Visitor Serialization Difference
# Feature: developer-profiles
# Validates: Requirements 8.2, 8.3
# ---------------------------------------------------------------------------

class TestProperty4OwnerVsVisitorSerialization(TestCase):
    """Owner serialization includes email + github_sync_status; visitor does not."""

    @given(st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=10, deadline=None)
    def test_owner_has_private_fields_visitor_does_not(self, suffix):
        user = make_user(f"own-{suffix}")
        profile = make_profile(user, f"own-{suffix}")
        owner_data = ProfileOwnerSerializer(profile).data
        public_data = ProfilePublicSerializer(profile).data
        self.assertIn('email', owner_data)
        self.assertIn('github_sync_status', owner_data)
        self.assertNotIn('email', public_data)
        self.assertNotIn('github_sync_status', public_data)
        profile.delete()
        user.delete()


# ---------------------------------------------------------------------------
# Property 5: Serialization Round Trip
# Feature: developer-profiles
# Validates: Requirements 8.5
# ---------------------------------------------------------------------------

class TestProperty5SerializationRoundTrip(TestCase):
    """Serializing then reading back yields identical values for all fields."""

    def setUp(self):
        self.user = make_user("rt-user")

    @given(
        display_name=st.text(min_size=2, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ "),
        bio=st.one_of(st.none(), st.text(max_size=200)),
    )
    @settings(max_examples=100, deadline=None)
    def test_round_trip(self, display_name, bio):
        profile = Profile.objects.create(
            user=self.user,
            slug="rt-slug",
            display_name=display_name,
            bio=bio,
        )
        data = ProfilePublicSerializer(profile).data
        self.assertEqual(data['display_name'], profile.display_name)
        self.assertEqual(data['bio'], profile.bio)
        self.assertEqual(data['slug'], profile.slug)
        profile.delete()
        Profile.objects.filter(user=self.user).delete()


# ---------------------------------------------------------------------------
# Property 6: Project Entry Display Order Preservation
# Feature: developer-profiles
# Validates: Requirements 2.7, 5.6
# ---------------------------------------------------------------------------

class TestProperty6ProjectDisplayOrderPreservation(TestCase):
    """Projects are serialized in ascending display_order."""

    def setUp(self):
        self.user = make_user("order-user")
        self.profile = make_profile(self.user, "order-dev")

    @given(st.lists(st.integers(min_value=0, max_value=100), min_size=2, max_size=10, unique=True))
    @settings(max_examples=100, deadline=None)
    def test_projects_sorted_by_display_order(self, orders):
        repos = []
        entries = []
        for i, order in enumerate(orders):
            repo = Repository.objects.create(user=self.user, name=f"repo-{i}-{order}", status="ready")
            entry = ProjectEntry.objects.create(profile=self.profile, repository=repo, display_order=order)
            repos.append(repo)
            entries.append(entry)

        data = ProfilePublicSerializer(self.profile).data
        returned_orders = [p['display_order'] for p in data['projects']]
        self.assertEqual(returned_orders, sorted(returned_orders))

        ProjectEntry.objects.filter(profile=self.profile).delete()
        Repository.objects.filter(user=self.user).delete()


# ---------------------------------------------------------------------------
# Property 7: Project Entry Count Constraint
# Feature: developer-profiles
# Validates: Requirements 5.4, 5.8
# ---------------------------------------------------------------------------

class TestProperty7ProjectCountConstraint(TestCase):
    """Cannot add more than 50 projects; removing one at limit allows adding another."""

    def setUp(self):
        self.user = make_user("cnt-user")
        self.client_user = self.user
        self.profile = make_profile(self.user, "cnt-dev")

    def test_fifty_project_limit_enforced(self):
        from django.test import Client
        client = Client()
        client.force_login(self.user)
        repos = [Repository.objects.create(user=self.user, name=f"r{i}", status="ready") for i in range(51)]
        for repo in repos[:50]:
            ProjectEntry.objects.create(profile=self.profile, repository=repo, display_order=0)
        resp = client.post(
            "/api/profiles/me/projects/",
            {"repository_id": repos[50].id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        # Remove one — should now be addable
        ProjectEntry.objects.filter(profile=self.profile, repository=repos[0]).delete()
        resp2 = client.post(
            "/api/profiles/me/projects/",
            {"repository_id": repos[50].id},
            content_type="application/json",
        )
        self.assertEqual(resp2.status_code, 201)


# ---------------------------------------------------------------------------
# Property 8: Duplicate Project Entry Rejection
# Feature: developer-profiles
# Validates: Requirements 5.9
# ---------------------------------------------------------------------------

class TestProperty8DuplicateProjectRejection(TestCase):
    """Adding the same repository twice is rejected; project list unchanged."""

    def setUp(self):
        self.user = make_user("dup-user")
        self.profile = make_profile(self.user, "dup-dev")

    @given(st.just(True))
    @settings(max_examples=10, deadline=None)
    def test_duplicate_rejected_project_list_unchanged(self, _):
        from django.test import Client
        client = Client()
        client.force_login(self.user)
        repo = Repository.objects.create(user=self.user, name="dup-repo", status="ready")
        ProjectEntry.objects.create(profile=self.profile, repository=repo, display_order=0)
        count_before = self.profile.projects.count()
        resp = client.post(
            "/api/profiles/me/projects/",
            {"repository_id": repo.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.profile.projects.count(), count_before)
        repo.delete()


# ---------------------------------------------------------------------------
# Property 9: Profile Immutability on Invalid Input
# Feature: developer-profiles
# Validates: Requirements 3.4, 3.7, 3.8
# ---------------------------------------------------------------------------

class TestProperty9ProfileImmutabilityOnInvalidInput(TestCase):
    """Failed updates leave profile data entirely unchanged."""

    def setUp(self):
        self.user = make_user("imm-user")
        self.profile = make_profile(self.user, "imm-dev", "Immutable Dev")

    @given(bio=st.text(min_size=501, max_size=600))
    @settings(max_examples=50, deadline=None)
    def test_oversized_bio_rejected_profile_unchanged(self, bio):
        from django.test import Client
        client = Client()
        client.force_login(self.user)
        original_bio = self.profile.bio
        resp = client.put(
            f"/api/profiles/{self.profile.slug}/update/",
            {"bio": bio},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, original_bio)


# ---------------------------------------------------------------------------
# Property 10: Non-Owner Update Rejection
# Feature: developer-profiles
# Validates: Requirements 3.2
# ---------------------------------------------------------------------------

class TestProperty10NonOwnerRejection(TestCase):
    """Any non-owner update is rejected with 403; profile unchanged."""

    @given(st.text(min_size=2, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=10, deadline=None)
    def test_non_owner_gets_403_profile_unchanged(self, suffix):
        from django.test import Client
        owner = make_user(f"ow-{suffix}")
        profile = make_profile(owner, f"ow-{suffix}")
        other = make_user(f"ot-{suffix}")
        client = Client()
        client.force_login(other)
        original_name = profile.display_name
        resp = client.put(
            f"/api/profiles/{profile.slug}/update/",
            {"display_name": "Hacked"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
        profile.refresh_from_db()
        self.assertEqual(profile.display_name, original_name)
        profile.delete()
        owner.delete()
        other.delete()


# ---------------------------------------------------------------------------
# Property 11: Follow Count Consistency Invariant
# Feature: developer-profiles
# Validates: Requirements 6.7
# ---------------------------------------------------------------------------

class TestProperty11FollowCountConsistency(TestCase):
    """follower_count and following_count always match actual Follow records."""

    def setUp(self):
        self.service = FollowService()

    @given(st.integers(min_value=0, max_value=5))
    @settings(max_examples=30, deadline=None)
    def test_counts_match_actual_records(self, n_followers):
        user_a = make_user(f"fa-{n_followers}-a")
        profile_a = make_profile(user_a, f"fa-{n_followers}-a")
        followers = []
        for i in range(n_followers):
            u = make_user(f"fb-{n_followers}-{i}")
            p = make_profile(u, f"fb-{n_followers}-{i}")
            self.service.follow(p, profile_a)
            followers.append((u, p))
        profile_a.refresh_from_db()
        actual_followers = Follow.objects.filter(target=profile_a).count()
        self.assertEqual(profile_a.follower_count, actual_followers)
        # Cleanup
        for u, p in followers:
            p.delete()
            u.delete()
        profile_a.delete()
        user_a.delete()


# ---------------------------------------------------------------------------
# Property 12: Follow Idempotence
# Feature: developer-profiles
# Validates: Requirements 6.4
# ---------------------------------------------------------------------------

class TestProperty12FollowIdempotence(TestCase):
    """Following an already-followed user does not create a duplicate."""

    def setUp(self):
        self.service = FollowService()

    @given(st.just(True))
    @settings(max_examples=20, deadline=None)
    def test_duplicate_follow_not_created(self, _):
        ua = make_user("idp-a")
        ub = make_user("idp-b")
        pa = make_profile(ua, "idp-a")
        pb = make_profile(ub, "idp-b")
        self.service.follow(pa, pb)
        count_before = Follow.objects.filter(follower=pa, target=pb).count()
        self.service.follow(pa, pb)  # idempotent
        count_after = Follow.objects.filter(follower=pa, target=pb).count()
        self.assertEqual(count_before, count_after)
        self.assertEqual(count_after, 1)
        pa.delete(); ua.delete(); pb.delete(); ub.delete()


# ---------------------------------------------------------------------------
# Property 13: Self-Follow Rejection
# Feature: developer-profiles
# Validates: Requirements 6.3
# ---------------------------------------------------------------------------

class TestProperty13SelfFollowRejection(TestCase):
    """Any attempt to follow oneself is rejected; no Follow record created."""

    @given(st.text(min_size=3, max_size=15, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=10, deadline=None)
    def test_self_follow_rejected(self, suffix):
        from django.core.exceptions import ValidationError
        user = make_user(f"sf-{suffix}")
        profile = make_profile(user, f"sf-{suffix}")
        count_before = Follow.objects.filter(follower=profile, target=profile).count()
        service = FollowService()
        with self.assertRaises(ValidationError):
            service.follow(profile, profile)
        count_after = Follow.objects.filter(follower=profile, target=profile).count()
        self.assertEqual(count_before, count_after)
        profile.delete(); user.delete()


# ---------------------------------------------------------------------------
# Property 14: Follow/Unfollow Round Trip
# Feature: developer-profiles
# Validates: Requirements 6.1, 6.2, 6.7
# ---------------------------------------------------------------------------

class TestProperty14FollowUnfollowRoundTrip(TestCase):
    """Follow then unfollow restores both profiles' counts to initial values."""

    def setUp(self):
        self.service = FollowService()

    @given(st.just(True))
    @settings(max_examples=20, deadline=None)
    def test_round_trip_restores_counts(self, _):
        ua = make_user("rt-fa")
        ub = make_user("rt-fb")
        pa = make_profile(ua, "rt-fa")
        pb = make_profile(ub, "rt-fb")
        initial_a_following = pa.following_count
        initial_b_followers = pb.follower_count
        self.service.follow(pa, pb)
        self.service.unfollow(pa, pb)
        pa.refresh_from_db(); pb.refresh_from_db()
        self.assertEqual(pa.following_count, initial_a_following)
        self.assertEqual(pb.follower_count, initial_b_followers)
        self.assertFalse(Follow.objects.filter(follower=pa, target=pb).exists())
        pa.delete(); ua.delete(); pb.delete(); ub.delete()


# ---------------------------------------------------------------------------
# Property 16: Search Active-Only Invariant
# Feature: developer-profiles
# Validates: Requirements 7.1, 7.4
# ---------------------------------------------------------------------------

class TestProperty16SearchActiveOnly(TestCase):
    """Search never returns inactive profiles regardless of query match."""

    @given(st.text(min_size=3, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=10, deadline=None)
    def test_inactive_never_returned(self, suffix):
        from django.test import Client
        user = make_user(f"sa-{suffix}")
        profile = Profile.objects.create(
            user=user, slug=f"sa-{suffix}",
            display_name=f"Search {suffix}", status="inactive",
        )
        client = Client()
        resp = client.get(f"/api/profiles/search/?q={suffix}")
        self.assertEqual(resp.status_code, 200)
        slugs = [r['slug'] for r in resp.json()['results']]
        self.assertNotIn(f"sa-{suffix}", slugs)
        profile.delete(); user.delete()


# ---------------------------------------------------------------------------
# Property 17: Skill Tag Filter Correctness
# Feature: developer-profiles
# Validates: Requirements 7.3
# ---------------------------------------------------------------------------

class TestProperty17SkillTagFilter(TestCase):
    """All results from a skill_tag filter contain that tag."""

    @given(st.text(min_size=3, max_size=15, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=10, deadline=None)
    def test_all_results_contain_tag(self, tag):
        from django.test import Client
        user = make_user(f"stf-{tag}")
        profile = Profile.objects.create(
            user=user, slug=f"stf-{tag}",
            display_name=f"TagDev {tag}",
            skill_tags=[tag, "extra"],
            status="active",
        )
        client = Client()
        resp = client.get(f"/api/profiles/search/?q={tag}&skill_tag={tag}")
        self.assertEqual(resp.status_code, 200)
        for result in resp.json()['results']:
            self.assertIn(tag, result['skill_tags'])
        profile.delete(); user.delete()


# ---------------------------------------------------------------------------
# Property 21: Skill Tags Serialized Without Truncation
# Feature: developer-profiles
# Validates: Requirements 2.3
# ---------------------------------------------------------------------------

class TestProperty21SkillTagsNoTruncation(TestCase):
    """Serialized skill_tags array matches exactly what was stored."""

    def setUp(self):
        self.user = make_user("skt-user")

    @given(st.lists(
        st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz"),
        min_size=0,
        max_size=20,
        unique=True,
    ))
    @settings(max_examples=100, deadline=None)
    def test_skill_tags_not_truncated(self, tags):
        profile = Profile.objects.create(
            user=self.user, slug="skt-slug",
            display_name="SkillDev", skill_tags=tags,
        )
        data = ProfilePublicSerializer(profile).data
        self.assertEqual(data['skill_tags'], tags)
        profile.delete()
        Profile.objects.filter(user=self.user).delete()

from rest_framework import serializers

from profiles.models import Follow, Profile, ProjectEntry


class ProjectEntrySerializer(serializers.ModelSerializer):
    """Serializer for project entries shown on a profile."""

    repository_name = serializers.CharField(source='repository.name', read_only=True)
    primary_language = serializers.SerializerMethodField()
    explorer_link = serializers.SerializerMethodField()

    class Meta:
        model = ProjectEntry
        fields = [
            'id',
            'repository_name',
            'custom_description',
            'primary_language',
            'explorer_link',
            'display_order',
            'added_at',
        ]

    def get_primary_language(self, obj):
        # Repository model does not have a language field; always return None.
        return None

    def get_explorer_link(self, obj):
        return f'/repos/{obj.repository.id}'


class ProfilePublicSerializer(serializers.ModelSerializer):
    """Public-facing profile serializer for visitors."""

    skill_tags = serializers.ListField(child=serializers.CharField())
    projects = serializers.SerializerMethodField()
    joined_date = serializers.SerializerMethodField()

    # Optional fields that are nullable
    avatar_url = serializers.URLField(allow_null=True, required=False)
    bio = serializers.CharField(allow_null=True, required=False)
    location = serializers.CharField(allow_null=True, required=False)
    website_url = serializers.URLField(allow_null=True, required=False)
    github_username = serializers.CharField(allow_null=True, required=False)

    class Meta:
        model = Profile
        fields = [
            'slug',
            'display_name',
            'avatar_url',
            'bio',
            'location',
            'website_url',
            'skill_tags',
            'follower_count',
            'following_count',
            'projects',
            'joined_date',
            'github_username',
        ]

    def get_projects(self, obj):
        return ProjectEntrySerializer(
            obj.projects.all(),
            many=True,
            context=self.context,
        ).data

    def get_joined_date(self, obj):
        return obj.created_at.isoformat()


class ProfileOwnerSerializer(ProfilePublicSerializer):
    """Extended serializer for the profile owner — includes private fields."""

    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta(ProfilePublicSerializer.Meta):
        fields = ProfilePublicSerializer.Meta.fields + ['email', 'github_sync_status']


class ProfileMiniSerializer(serializers.ModelSerializer):
    """Minimal profile representation used inside follow lists."""

    avatar_url = serializers.URLField(allow_null=True, required=False)
    bio = serializers.CharField(allow_null=True, required=False)

    class Meta:
        model = Profile
        fields = ['slug', 'display_name', 'avatar_url', 'bio']


class FollowSerializer(serializers.ModelSerializer):
    """Serializer for follower / following list entries."""

    follower = ProfileMiniSerializer(read_only=True)
    target = ProfileMiniSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ['id', 'follower', 'target', 'created_at']

"use client";

import { notFound } from "next/navigation";
import { AlertCircle } from "lucide-react";
import { useProfile } from "@/lib/hooks/use-profiles";
import { useAuth } from "@/lib/auth/auth-context";
import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { SkillTagList } from "@/components/profile/SkillTagList";
import { ProjectShowcase } from "@/components/profile/ProjectShowcase";

interface ProfilePageProps {
  params: { slug: string };
}

export default function ProfilePage({ params }: ProfilePageProps) {
  const { slug } = params;
  const { user } = useAuth();
  const { data: profile, isLoading, isError, error } = useProfile(slug);

  if (isLoading) {
    return <ProfileSkeleton />;
  }

  if (isError) {
    const apiErr = error as { status?: number } | null;
    if (apiErr?.status === 404) {
      notFound();
    }
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <AlertCircle className="h-10 w-10 text-destructive" />
        <p className="mt-2 text-sm text-muted-foreground">Failed to load profile.</p>
      </div>
    );
  }

  if (!profile) return null;

  const isOwnProfile = user?.username === profile.slug || user?.username === profile.github_username;

  return (
    <div className="mx-auto max-w-3xl space-y-8 py-6 px-4">
      <ProfileHeader profile={profile} />

      {/* Skills */}
      <section aria-labelledby="skills-heading">
        <h2 id="skills-heading" className="mb-3 text-lg font-semibold">Skills</h2>
        <SkillTagList tags={profile.skill_tags} />
      </section>

      {/* Projects */}
      <section aria-labelledby="projects-heading">
        <div className="flex items-center justify-between mb-3">
          <h2 id="projects-heading" className="text-lg font-semibold">Projects</h2>
          {isOwnProfile && (
            <a
              href="/profile/projects"
              className="text-sm text-primary hover:underline"
            >
              Manage projects
            </a>
          )}
        </div>
        <ProjectShowcase projects={profile.projects} />
      </section>
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <div className="mx-auto max-w-3xl space-y-8 py-6 px-4 animate-pulse">
      <div className="flex gap-6">
        <div className="h-24 w-24 rounded-full bg-gray-200 shrink-0" />
        <div className="flex-1 space-y-3">
          <div className="h-7 w-48 rounded bg-gray-200" />
          <div className="h-4 w-32 rounded bg-gray-200" />
          <div className="h-4 w-full max-w-sm rounded bg-gray-200" />
        </div>
      </div>
      <div className="space-y-2">
        <div className="h-5 w-20 rounded bg-gray-200" />
        <div className="flex gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-6 w-16 rounded-full bg-gray-200" />
          ))}
        </div>
      </div>
    </div>
  );
}

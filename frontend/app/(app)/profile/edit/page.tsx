"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AuthGuard } from "@/lib/auth/auth-guard";
import { useMyProfile, useUpdateProfile } from "@/lib/hooks/use-profiles";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ProfileUpdateData } from "@/lib/types/profiles";

function ProfileEditContent() {
  const router = useRouter();
  const { data: profile, isLoading } = useMyProfile();
  const { mutate: updateProfile, isPending } = useUpdateProfile(profile?.slug ?? "");

  const [formData, setFormData] = useState<ProfileUpdateData>({});
  const [skillInput, setSkillInput] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [successMsg, setSuccessMsg] = useState("");

  if (isLoading || !profile) {
    return <div className="animate-pulse h-64 rounded bg-gray-100" />;
  }

  const currentTags = formData.skill_tags ?? profile.skill_tags;

  function set(field: keyof ProfileUpdateData, value: string | null) {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: "" }));
    setSuccessMsg("");
  }

  function addTag() {
    const tag = skillInput.trim();
    if (!tag || tag.length > 50) return;
    if (currentTags.length >= 20) return;
    setFormData((prev) => ({ ...prev, skill_tags: [...currentTags, tag] }));
    setSkillInput("");
  }

  function removeTag(tag: string) {
    setFormData((prev) => ({ ...prev, skill_tags: currentTags.filter((t) => t !== tag) }));
  }

  function handleSave() {
    if (Object.keys(formData).length === 0) return;
    updateProfile(formData, {
      onSuccess: (updated) => {
        setFormData({});
        setSuccessMsg("Profile updated.");
        if (formData.slug && formData.slug !== profile?.slug) {
          router.replace(`/profile/edit`);
        }
      },
      onError: (err: unknown) => {
        const apiErr = err as { fields?: Record<string, string[]> };
        if (apiErr?.fields) {
          const flat: Record<string, string> = {};
          for (const [k, v] of Object.entries(apiErr.fields)) {
            flat[k] = Array.isArray(v) ? v[0] : String(v);
          }
          setFieldErrors(flat);
        }
      },
    });
  }

  return (
    <div className="mx-auto max-w-lg space-y-6 py-8 px-4">
      <h1 className="text-2xl font-bold">Edit Profile</h1>

      {successMsg && (
        <p className="text-sm text-green-600">{successMsg}</p>
      )}

      <div className="space-y-4">
        <div className="space-y-1">
          <Label htmlFor="display_name">Display name</Label>
          <Input
            id="display_name"
            defaultValue={profile.display_name}
            onChange={(e) => set("display_name", e.target.value)}
            maxLength={100}
          />
          {fieldErrors.display_name && (
            <p className="text-xs text-destructive">{fieldErrors.display_name}</p>
          )}
        </div>

        <div className="space-y-1">
          <Label htmlFor="slug">Profile slug</Label>
          <Input
            id="slug"
            defaultValue={profile.slug}
            onChange={(e) => set("slug", e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
            maxLength={40}
          />
          {fieldErrors.slug && (
            <p className="text-xs text-destructive">{fieldErrors.slug}</p>
          )}
        </div>

        <div className="space-y-1">
          <Label htmlFor="bio">Bio</Label>
          <textarea
            id="bio"
            className="w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[100px] resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            defaultValue={profile.bio ?? ""}
            onChange={(e) => set("bio", e.target.value || null)}
            maxLength={500}
          />
        </div>

        <div className="space-y-1">
          <Label htmlFor="location">Location</Label>
          <Input
            id="location"
            defaultValue={profile.location ?? ""}
            onChange={(e) => set("location", e.target.value || null)}
            maxLength={100}
          />
        </div>

        <div className="space-y-1">
          <Label htmlFor="website_url">Website</Label>
          <Input
            id="website_url"
            type="url"
            defaultValue={profile.website_url ?? ""}
            onChange={(e) => set("website_url", e.target.value || null)}
            maxLength={200}
          />
          {fieldErrors.website_url && (
            <p className="text-xs text-destructive">{fieldErrors.website_url}</p>
          )}
        </div>

        <div className="space-y-1">
          <Label>Skills</Label>
          <div className="flex gap-2">
            <Input
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
              placeholder="Add a skill"
              maxLength={50}
            />
            <Button type="button" variant="outline" onClick={addTag}>Add</Button>
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {currentTags.map((tag) => (
              <button
                key={tag}
                onClick={() => removeTag(tag)}
                className="rounded-full bg-secondary px-3 py-1 text-xs hover:bg-destructive hover:text-destructive-foreground transition-colors"
                aria-label={`Remove ${tag}`}
              >
                {tag} ×
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <Button variant="outline" onClick={() => router.back()}>Cancel</Button>
        <Button onClick={handleSave} disabled={isPending || Object.keys(formData).length === 0}>
          {isPending ? "Saving..." : "Save Changes"}
        </Button>
      </div>
    </div>
  );
}

export default function ProfileEditPage() {
  return (
    <AuthGuard>
      <ProfileEditContent />
    </AuthGuard>
  );
}

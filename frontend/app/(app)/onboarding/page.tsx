"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AuthGuard } from "@/lib/auth/auth-guard";
import { useCreateProfile } from "@/lib/hooks/use-profiles";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ProfileCreateData } from "@/lib/types/profiles";

function OnboardingContent() {
  const router = useRouter();
  const { mutate: createProfile, isPending, error } = useCreateProfile();

  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<ProfileCreateData>({
    display_name: "",
    slug: "",
    bio: "",
    location: "",
    website_url: "",
    skill_tags: [],
  });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [skillInput, setSkillInput] = useState("");

  function handleChange(field: keyof ProfileCreateData, value: string) {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (fieldErrors[field]) {
      setFieldErrors((prev) => ({ ...prev, [field]: "" }));
    }
  }

  function addSkillTag() {
    const tag = skillInput.trim();
    if (!tag) return;
    if (tag.length > 50) {
      setFieldErrors((prev) => ({ ...prev, skill_tags: "Tag must be 50 characters or fewer." }));
      return;
    }
    const current = formData.skill_tags ?? [];
    if (current.length >= 20) {
      setFieldErrors((prev) => ({ ...prev, skill_tags: "Maximum 20 skill tags." }));
      return;
    }
    setFormData((prev) => ({ ...prev, skill_tags: [...(prev.skill_tags ?? []), tag] }));
    setSkillInput("");
    setFieldErrors((prev) => ({ ...prev, skill_tags: "" }));
  }

  function removeSkillTag(tag: string) {
    setFormData((prev) => ({
      ...prev,
      skill_tags: (prev.skill_tags ?? []).filter((t) => t !== tag),
    }));
  }

  function validateStep1(): boolean {
    const errors: Record<string, string> = {};
    if (!formData.display_name || formData.display_name.length < 2 || formData.display_name.length > 100) {
      errors.display_name = "Display name must be 2–100 characters.";
    }
    if (!formData.slug) {
      errors.slug = "Slug is required.";
    } else if (!/^[a-z][a-z0-9\-]{2,39}$/.test(formData.slug)) {
      errors.slug = "Slug must start with a lowercase letter, 3–40 characters, only a-z, 0-9, and hyphens.";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleNext() {
    if (step === 1 && !validateStep1()) return;
    setStep((s) => s + 1);
  }

  function handleSubmit() {
    const payload: ProfileCreateData = {
      display_name: formData.display_name,
      slug: formData.slug,
    };
    if (formData.bio) payload.bio = formData.bio;
    if (formData.location) payload.location = formData.location;
    if (formData.website_url) payload.website_url = formData.website_url;
    if (formData.skill_tags?.length) payload.skill_tags = formData.skill_tags;

    createProfile(payload, {
      onSuccess: (profile) => {
        router.push(`/${profile.slug}`);
      },
      onError: (err: unknown) => {
        const apiErr = err as { fields?: Record<string, string[]> };
        if (apiErr?.fields) {
          const flat: Record<string, string> = {};
          for (const [k, v] of Object.entries(apiErr.fields)) {
            flat[k] = Array.isArray(v) ? v[0] : String(v);
          }
          setFieldErrors(flat);
          setStep(1);
        }
      },
    });
  }

  return (
    <div className="mx-auto max-w-lg py-12 px-4 space-y-8">
      <div className="text-center space-y-1">
        <h1 className="text-2xl font-bold">Create your developer profile</h1>
        <p className="text-sm text-muted-foreground">Step {step} of 3</p>
      </div>

      {/* Step 1: Required fields */}
      {step === 1 && (
        <div className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="display_name">Display name *</Label>
            <Input
              id="display_name"
              value={formData.display_name}
              onChange={(e) => handleChange("display_name", e.target.value)}
              placeholder="e.g. Jane Developer"
              maxLength={100}
              aria-describedby={fieldErrors.display_name ? "dn-err" : undefined}
            />
            {fieldErrors.display_name && (
              <p id="dn-err" className="text-xs text-destructive">{fieldErrors.display_name}</p>
            )}
          </div>

          <div className="space-y-1">
            <Label htmlFor="slug">Profile slug *</Label>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">devsuper.app/</span>
              <Input
                id="slug"
                value={formData.slug}
                onChange={(e) => handleChange("slug", e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                placeholder="jane-dev"
                maxLength={40}
                aria-describedby={fieldErrors.slug ? "slug-err" : undefined}
              />
            </div>
            {fieldErrors.slug && (
              <p id="slug-err" className="text-xs text-destructive">{fieldErrors.slug}</p>
            )}
          </div>

          <Button className="w-full" onClick={handleNext}>Next</Button>
        </div>
      )}

      {/* Step 2: Optional bio and location */}
      {step === 2 && (
        <div className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="bio">Bio <span className="text-muted-foreground">(optional)</span></Label>
            <textarea
              id="bio"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[100px] resize-none focus:outline-none focus:ring-2 focus:ring-ring"
              value={formData.bio ?? ""}
              onChange={(e) => handleChange("bio", e.target.value)}
              placeholder="Tell developers about yourself..."
              maxLength={500}
            />
            <p className="text-xs text-muted-foreground text-right">{(formData.bio ?? "").length}/500</p>
          </div>

          <div className="space-y-1">
            <Label htmlFor="location">Location <span className="text-muted-foreground">(optional)</span></Label>
            <Input
              id="location"
              value={formData.location ?? ""}
              onChange={(e) => handleChange("location", e.target.value)}
              placeholder="e.g. San Francisco, CA"
              maxLength={100}
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="website_url">Website <span className="text-muted-foreground">(optional)</span></Label>
            <Input
              id="website_url"
              type="url"
              value={formData.website_url ?? ""}
              onChange={(e) => handleChange("website_url", e.target.value)}
              placeholder="https://yoursite.com"
              maxLength={200}
            />
          </div>

          <div className="flex gap-2">
            <Button variant="outline" className="flex-1" onClick={() => setStep(1)}>Back</Button>
            <Button className="flex-1" onClick={handleNext}>Next</Button>
          </div>
        </div>
      )}

      {/* Step 3: Skill tags */}
      {step === 3 && (
        <div className="space-y-4">
          <div className="space-y-1">
            <Label>Skills <span className="text-muted-foreground">(optional, max 20)</span></Label>
            <div className="flex gap-2">
              <Input
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addSkillTag(); } }}
                placeholder="e.g. Python, React, Rust"
                maxLength={50}
              />
              <Button type="button" variant="outline" onClick={addSkillTag}>Add</Button>
            </div>
            {fieldErrors.skill_tags && (
              <p className="text-xs text-destructive">{fieldErrors.skill_tags}</p>
            )}
            <div className="flex flex-wrap gap-2 mt-2">
              {(formData.skill_tags ?? []).map((tag) => (
                <button
                  key={tag}
                  onClick={() => removeSkillTag(tag)}
                  className="rounded-full bg-secondary px-3 py-1 text-xs hover:bg-destructive hover:text-destructive-foreground transition-colors"
                  aria-label={`Remove ${tag}`}
                >
                  {tag} ×
                </button>
              ))}
            </div>
          </div>

          {error && (
            <p className="text-sm text-destructive">
              Failed to create profile. Please try again.
            </p>
          )}

          <div className="flex gap-2">
            <Button variant="outline" className="flex-1" onClick={() => setStep(2)}>Back</Button>
            <Button className="flex-1" onClick={handleSubmit} disabled={isPending}>
              {isPending ? "Creating..." : "Create Profile"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <AuthGuard>
      <OnboardingContent />
    </AuthGuard>
  );
}

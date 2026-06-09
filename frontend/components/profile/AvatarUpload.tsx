"use client";

import { useState } from "react";
import Image from "next/image";
import { UserCircle2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface AvatarUploadProps {
  currentUrl: string | null;
  onUrlChange: (url: string | null) => void;
  error?: string;
}

/**
 * Avatar section for the profile edit form.
 * Allows entering a URL directly (PNG/JPEG/WebP, max 2MB implied by URL entry).
 */
export function AvatarUpload({ currentUrl, onUrlChange, error }: AvatarUploadProps) {
  const [inputUrl, setInputUrl] = useState(currentUrl ?? "");
  const [preview, setPreview] = useState(currentUrl);

  function handleUrlChange(val: string) {
    setInputUrl(val);
    const trimmed = val.trim() || null;
    onUrlChange(trimmed);
    setPreview(trimmed);
  }

  return (
    <div className="space-y-3">
      <Label>Avatar</Label>

      <div className="flex items-center gap-4">
        {preview ? (
          <Image
            src={preview}
            alt="Avatar preview"
            width={64}
            height={64}
            className="h-16 w-16 rounded-full object-cover border"
            unoptimized
            onError={() => setPreview(null)}
          />
        ) : (
          <UserCircle2 className="h-16 w-16 text-muted-foreground" />
        )}

        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <Upload className="h-4 w-4 text-muted-foreground shrink-0" />
            <Input
              type="url"
              value={inputUrl}
              onChange={(e) => handleUrlChange(e.target.value)}
              placeholder="https://example.com/avatar.png"
              maxLength={500}
              aria-label="Avatar URL"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            PNG, JPEG, or WebP. Enter a direct image URL.
          </p>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
      </div>

      {preview && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="text-xs text-destructive"
          onClick={() => { setPreview(null); setInputUrl(""); onUrlChange(null); }}
        >
          Remove avatar
        </Button>
      )}
    </div>
  );
}

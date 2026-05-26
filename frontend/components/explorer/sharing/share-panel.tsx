"use client";

import * as React from "react";
import { Copy, Check, RefreshCw, Link } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import {
  useEnableSharing,
  useDisableSharing,
  useRegenerateShareUrl,
} from "@/lib/hooks/use-sharing";
import type { ShareInfo } from "@/lib/types/api";

export interface SharePanelProps {
  repoId: number;
  currentShareInfo: ShareInfo | null;
}

export function SharePanel({ repoId, currentShareInfo }: SharePanelProps) {
  const [copied, setCopied] = React.useState(false);
  const [showRegenerateDialog, setShowRegenerateDialog] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const enableSharing = useEnableSharing(repoId);
  const disableSharing = useDisableSharing(repoId);
  const regenerateUrl = useRegenerateShareUrl(repoId);

  const isActive = currentShareInfo?.isActive ?? false;
  const isMutating =
    enableSharing.isPending ||
    disableSharing.isPending ||
    regenerateUrl.isPending;

  const handleToggle = (checked: boolean) => {
    setError(null);
    if (checked) {
      enableSharing.mutate(undefined, {
        onError: (err) => {
          setError(err.message || "Failed to enable sharing");
        },
      });
    } else {
      disableSharing.mutate(undefined, {
        onError: (err) => {
          setError(err.message || "Failed to disable sharing");
        },
      });
    }
  };

  const handleCopy = async () => {
    if (!currentShareInfo?.url) return;

    try {
      await navigator.clipboard.writeText(currentShareInfo.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch {
      setError("Failed to copy to clipboard");
    }
  };

  const handleRegenerate = () => {
    setShowRegenerateDialog(true);
  };

  const confirmRegenerate = () => {
    setError(null);
    setShowRegenerateDialog(false);
    regenerateUrl.mutate(undefined, {
      onError: (err) => {
        setError(err.message || "Failed to regenerate share URL");
      },
    });
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Link className="h-5 w-5" />
            Public Sharing
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="share-toggle">Enable public access</Label>
            <Switch
              id="share-toggle"
              checked={isActive}
              onCheckedChange={handleToggle}
              disabled={isMutating}
              aria-label="Toggle public sharing"
            />
          </div>

          {isActive && currentShareInfo && (
            <div className="space-y-3">
              <div className="flex gap-2">
                <Input
                  value={currentShareInfo.url}
                  readOnly
                  className="font-mono text-sm"
                  aria-label="Share URL"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleCopy}
                  disabled={isMutating}
                  aria-label={copied ? "Copied" : "Copy share URL"}
                >
                  {copied ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>

              {copied && (
                <p className="text-sm text-green-600" role="status">
                  Copied!
                </p>
              )}

              <Button
                variant="ghost"
                size="sm"
                onClick={handleRegenerate}
                disabled={isMutating}
                className="gap-2"
              >
                <RefreshCw
                  className={`h-4 w-4 ${regenerateUrl.isPending ? "animate-spin" : ""}`}
                />
                Regenerate URL
              </Button>
            </div>
          )}

          {isMutating && (
            <p className="text-sm text-muted-foreground">Updating...</p>
          )}

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
        </CardContent>
      </Card>

      <Dialog open={showRegenerateDialog} onOpenChange={setShowRegenerateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Regenerate Share URL</DialogTitle>
            <DialogDescription>
              Are you sure you want to regenerate the share URL? The previous URL
              will stop working and anyone with the old link will no longer be
              able to access the shared repository.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowRegenerateDialog(false)}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmRegenerate}>
              Regenerate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

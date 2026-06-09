"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Users, UserCircle2, ChevronLeft, ChevronRight } from "lucide-react";
import { useFollowers } from "@/lib/hooks/use-profiles";
import { Button } from "@/components/ui/button";

interface FollowersPageProps {
  params: { slug: string };
}

export default function FollowersPage({ params }: FollowersPageProps) {
  const { slug } = params;
  const [page, setPage] = useState(1);
  const { data, isLoading } = useFollowers(slug, page);

  return (
    <div className="mx-auto max-w-2xl space-y-6 py-8 px-4">
      <div className="flex items-center gap-2">
        <Link href={`/${slug}`} className="text-sm text-muted-foreground hover:underline">
          ← {slug}
        </Link>
        <span className="text-muted-foreground">/</span>
        <h1 className="text-xl font-bold">Followers</h1>
        {data && (
          <span className="text-sm text-muted-foreground">({data.count})</span>
        )}
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-3 animate-pulse">
              <div className="h-10 w-10 rounded-full bg-gray-200" />
              <div className="space-y-1 flex-1">
                <div className="h-4 w-32 rounded bg-gray-200" />
                <div className="h-3 w-48 rounded bg-gray-200" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && data && (
        <>
          {data.results.length === 0 ? (
            <div className="flex flex-col items-center py-16 text-center">
              <Users className="h-10 w-10 text-muted-foreground" />
              <p className="mt-2 text-sm text-muted-foreground">No followers yet.</p>
            </div>
          ) : (
            <ul className="divide-y">
              {data.results.map((follow) => {
                const person = follow.follower;
                return (
                  <li key={follow.id} className="py-4">
                    <Link href={`/${person.slug}`} className="flex items-center gap-3 hover:opacity-80 transition-opacity">
                      {person.avatar_url ? (
                        <Image src={person.avatar_url} alt={person.display_name} width={40} height={40} className="h-10 w-10 rounded-full object-cover" unoptimized />
                      ) : (
                        <UserCircle2 className="h-10 w-10 text-muted-foreground" />
                      )}
                      <div>
                        <p className="font-medium text-sm">{person.display_name}</p>
                        <p className="text-xs text-muted-foreground">@{person.slug}</p>
                        {person.bio && (
                          <p className="text-xs text-muted-foreground line-clamp-1">{person.bio}</p>
                        )}
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}

          {/* Pagination */}
          {(data.previous !== null || data.next !== null) && (
            <div className="flex items-center justify-between pt-4">
              <Button variant="outline" size="sm" disabled={data.previous === null} onClick={() => setPage((p) => p - 1)}>
                <ChevronLeft className="h-4 w-4 mr-1" /> Previous
              </Button>
              <span className="text-sm text-muted-foreground">Page {page}</span>
              <Button variant="outline" size="sm" disabled={data.next === null} onClick={() => setPage((p) => p + 1)}>
                Next <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

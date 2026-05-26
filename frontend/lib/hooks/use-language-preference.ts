"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { LanguageCode } from "@/lib/types/api";

/**
 * Mutation to update the user's language preference.
 * Invalidates the user/auth query cache on success so the UI
 * reflects the new preference.
 *
 * @returns UseMutationResult accepting a LanguageCode
 */
export function useUpdateLanguage() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, LanguageCode>({
    mutationFn: (language: LanguageCode) =>
      apiClient.put<void>(`/api/auth/language/`, { language }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["user"],
      });
    },
  });
}

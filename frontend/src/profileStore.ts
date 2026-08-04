import type { ProfileDraft } from "./completeness";

const KEY = "vanigam_profile";

export function emptyProfile(): ProfileDraft {
  return { founder: {}, startup: {}, docsVerified: false };
}

export function loadProfile(): ProfileDraft {
  const raw = localStorage.getItem(KEY);
  if (!raw) return emptyProfile();
  try {
    return { ...emptyProfile(), ...(JSON.parse(raw) as ProfileDraft) };
  } catch {
    return emptyProfile();
  }
}

export function saveProfile(p: ProfileDraft) {
  localStorage.setItem(KEY, JSON.stringify(p));
}

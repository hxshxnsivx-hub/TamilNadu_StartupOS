/* Class-name joiner.
   The shadcn convention is clsx + tailwind-merge; this project has no Tailwind,
   so there are no utility conflicts to resolve and a plain join is correct.
   Same call signature, so components written against shadcn drop straight in. */

export type ClassValue = string | number | null | false | undefined | ClassValue[];

export function cn(...inputs: ClassValue[]): string {
  const out: string[] = [];
  const walk = (v: ClassValue) => {
    if (!v && v !== 0) return;
    if (Array.isArray(v)) v.forEach(walk);
    else out.push(String(v));
  };
  inputs.forEach(walk);
  return out.join(" ");
}

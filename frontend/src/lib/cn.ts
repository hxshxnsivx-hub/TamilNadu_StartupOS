import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge class names, with later Tailwind utilities beating earlier ones.
 *
 * Plain string concatenation does NOT work for Tailwind: `"p-2" + " p-4"`
 * leaves both in the class list and the winner is decided by stylesheet
 * order, not by call order — so a component's default padding would beat
 * the override its caller passed in. twMerge resolves the conflict by
 * dropping the earlier utility from the same group.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

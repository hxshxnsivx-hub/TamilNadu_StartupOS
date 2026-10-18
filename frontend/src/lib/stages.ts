/* The one stage vocabulary, in order. Mirrors backend/app/core/stages.py;
   backend/tests/unit/test_stages.py fails if the two lists differ. */
export const STAGES = ["idea", "poc", "prototype", "mvp", "revenue", "growth", "scale"] as const;

export type Stage = (typeof STAGES)[number];

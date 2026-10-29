// Paper layout (P2): the blank working space under a question, the "Ans:" line with its unit,
// and where a question's marks print. The engine (render.py) draws the same thing into the PDF;
// these are the editor-side mirrors of its defaults so the page matches the paper.

export type MarksPlacement = "question" | "answer" | "both";
export const DEFAULT_PLACEMENT: MarksPlacement = "answer";

export interface PaperSettings {
  marks_placement?: MarksPlacement;
  /** Paper time in minutes (P4); printed in the paper header. */
  time_min?: number | null;
}

/** Pixels per millimetre on screen (CSS: 96 px per inch). */
export const PX_PER_MM = 96 / 25.4;
export const MAX_SPACE_MM = 250;

/** Blank working space for a question worth `marks`: 20 mm plus 15 mm a mark (engine mirror). */
export function defaultSpaceMm(marks: number | null | undefined): number {
  return 20 + 15 * Math.max(marks ?? 2, 1);
}

export const SPACE_PRESETS: Array<{ label: string; mm: number }> = [
  { label: "S", mm: 35 },
  { label: "M", mm: 60 },
  { label: "L", mm: 90 },
  { label: "XL", mm: 130 },
];

/** Round a drag result to 5 mm and keep it on the page. */
export function clampSpaceMm(mm: number): number {
  return Math.min(MAX_SPACE_MM, Math.max(0, Math.round(mm / 5) * 5));
}

/** The units a teacher can print after "Ans:" (the canonical vocabulary, with print labels). */
export const UNIT_CHOICES: Array<{ value: string; label: string }> = [
  { value: "", label: "none" },
  { value: "$", label: "$" },
  { value: "cents", label: "cents" },
  { value: "degrees", label: "°" },
  { value: "%", label: "%" },
  { value: "cm", label: "cm" },
  { value: "m", label: "m" },
  { value: "km", label: "km" },
  { value: "mm", label: "mm" },
  { value: "cm^2", label: "cm²" },
  { value: "m^2", label: "m²" },
  { value: "cm^3", label: "cm³" },
  { value: "m^3", label: "m³" },
  { value: "ml", label: "ml" },
  { value: "l", label: "l" },
  { value: "g", label: "g" },
  { value: "kg", label: "kg" },
  { value: "s", label: "s" },
  { value: "min", label: "min" },
  { value: "h", label: "h" },
  { value: "km/h", label: "km/h" },
  { value: "m/s", label: "m/s" },
  { value: "m/min", label: "m/min" },
  { value: "marbles", label: "marbles" },
  { value: "items", label: "items" },
  { value: "people", label: "people" },
  { value: "units", label: "units" },
];

/** What prints before and after the blank for `unit` (engine `unit_parts` mirror). */
export function unitParts(unit: string | null | undefined): {
  before: string;
  after: string;
} {
  if (!unit) return { before: "", after: "" };
  if (unit === "$") return { before: "$", after: "" };
  const hit = UNIT_CHOICES.find((u) => u.value === unit);
  return { before: "", after: hit ? hit.label : unit };
}

/** The per-question print layout a block carries in its attrs. */
export interface BlockLayout {
  space_mm: number | null;
  ans_unit: string | null;
}

export function layoutOf(
  attrs: Record<string, unknown> | undefined,
): BlockLayout {
  const mm = attrs?.space_mm;
  const unit = attrs?.ans_unit;
  return {
    space_mm: typeof mm === "number" ? mm : null,
    ans_unit: typeof unit === "string" ? unit : null,
  };
}

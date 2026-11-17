import type { Answer } from "./types";

/** How a unit code prints: the litre sign as on PSLE papers and real superscripts for area and
 *  volume, never a caret (engine units.PRINTED). */
export const PRINTED_UNIT: Record<string, string> = {
  l: "ℓ",
  ml: "mℓ",
  "cm^2": "cm²",
  "m^2": "m²",
  "cm^3": "cm³",
  "m^3": "m³",
};
const printed = (u: string): string => PRINTED_UNIT[u] ?? u;
const SUPERSCRIPT = "⁰¹²³⁴⁵⁶⁷⁸⁹";
const sup = (n: number): string => [...`${n}`].map((d) => SUPERSCRIPT[Number(d)]).join("");
const MINUS = "−"; // U+2212, as printed (a hyphen is not a minus sign)

/** Plain-text rendering of a typed answer (the web mirror of the engine's _fmt_answer). */
export function fmtAnswer(a: Answer | undefined): string {
  if (!a) return "";
  switch (a.type) {
    case "quantity":
    case "decimal":
    case "integer": {
      const u = a.unit ?? "";
      // Money renders at exactly 2 dp when it is a decimal amount (KAN-309).
      const shown =
        u === "$" && a.type === "decimal"
          ? Number(a.value).toFixed(2)
          : `${a.value}`;
      if (u === "$") return `$${shown}`;
      if (u === "degrees") return `${shown}°`;
      return u ? `${shown} ${printed(u)}` : `${shown}`;
    }
    case "fraction":
      return `${a.numerator}/${a.denominator}`;
    case "ratio":
      return (a.parts ?? []).join(" : ");
    case "set":
      return (a.values ?? []).join(", ");
    case "text":
      return a.text ?? "";
    case "choice": {
      const hit = (a.options ?? []).find((o) => o.label === a.correct);
      return hit?.text ? `${a.correct}. ${hit.text}` : `${a.correct ?? ""}`;
    }
    case "expression": {
      const terms = a.terms ?? [];
      const body = terms
        .map((t, i) => {
          const sym = t.symbol ?? "";
          const pow = sym && (t.power ?? 1) > 1 ? sup(t.power ?? 1) : "";
          const mag = Math.round(Math.abs(t.coefficient) * 1000) / 1000;
          const coef = sym && mag === 1 ? "" : `${mag}`;
          const neg = t.coefficient < 0;
          const sign = neg ? (i === 0 ? MINUS : ` ${MINUS} `) : i === 0 ? "" : " + ";
          return `${sign}${coef}${sym}${pow}`;
        })
        .join("");
      const u = a.unit ?? "";
      // A sum with a unit is bracketed so the unit cannot read as belonging to the last term.
      const group = terms.length > 1 && u ? `(${body})` : body;
      if (u === "$")
        return terms.length === 1 && terms[0].coefficient < 0
          ? `${MINUS}$${body.slice(1)}`
          : `$${group}`;
      if (u === "%") return `${group}%`;
      return u ? `${group} ${printed(u)}` : group;
    }
    default:
      return JSON.stringify(a);
  }
}

import type { CraftabilityScore } from "@/types";

export function inferHasUnfoldOverlap(
  hasUnfoldOverlap: boolean,
  craftability: CraftabilityScore | null,
): boolean {
  if (hasUnfoldOverlap) {
    return true;
  }
  return Boolean(
    craftability?.warnings.some((warning) => /unfold overlap/i.test(warning)),
  );
}

export function buildExportCautionMessage(
  exportBlocked: boolean,
  hasUnfoldOverlap: boolean,
): string | null {
  if (exportBlocked) {
    return "Layout overlaps block printing — fix overlaps before cutting.";
  }
  if (hasUnfoldOverlap) {
    return "Some pieces have unfold overlaps — review the template before printing.";
  }
  return null;
}

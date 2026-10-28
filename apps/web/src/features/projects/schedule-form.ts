import type {
  Fee,
  Installment,
  ProgressReading,
  ScheduleInput,
} from "./payment-schedule";
import type { ProjectDetail, ProjectSource } from "./types";

export type ScheduleLabels = Record<
  keyof typeof import("../../../messages/en.json").Schedule,
  string
>;

export type DeclaredReading = ProgressReading & { source: ProjectSource };

export type InstallmentRow = {
  id: string;
  kind: Installment["kind"];
  percent: string;
  date: string;
  progressPercent: string;
};

export type ScheduleForm = {
  price: string;
  rows: InstallmentRow[];
  useLoan: boolean;
  principal: string;
  rate: string;
  years: string;
};

// No official fee is cited yet: it is listed as unknown, never counted as zero.
export const SCHEDULE_FEES: Fee[] = [
  { id: "official_fees", status: "unknown" },
];

/**
 * Dated declared progress of the project-scope register readings, oldest first, each
 * value cited once by the first reading that stated it. Undated readings cannot place
 * a payment in time and are left out.
 */
export function declaredReadings(
  verification: ProjectDetail["verification"],
): DeclaredReading[] {
  if (!verification) return [];
  const candidates = [
    ...verification.register_readings,
    ...(verification.latest_reading ? [verification.latest_reading] : []),
  ];
  const seen = new Set<string>();
  const readings: DeclaredReading[] = [];
  for (const reading of candidates) {
    const percent = reading.progress_percent;
    const inspectedOn = reading.progress_inspected_on;
    if (percent === null || percent === undefined || !inspectedOn) continue;
    const key = `${inspectedOn}|${percent}`;
    if (seen.has(key)) continue;
    seen.add(key);
    readings.push({ inspectedOn, percent, source: reading.source });
  }
  return readings.toSorted(
    (a, b) =>
      a.inspectedOn.localeCompare(b.inspectedOn) || a.percent - b.percent,
  );
}

/** A number typed by the buyer; an empty field is missing, never zero. */
export function enteredNumber(text: string) {
  const trimmed = text.trim();
  return trimmed === "" ? Number.NaN : Number(trimmed);
}

function installment(row: InstallmentRow): Installment {
  const percent = enteredNumber(row.percent);
  if (row.kind === "on_date")
    return { kind: "on_date", percent, date: row.date };
  if (row.kind === "on_progress")
    return {
      kind: "on_progress",
      percent,
      progressPercent: enteredNumber(row.progressPercent),
    };
  return { kind: "on_handover", percent };
}

/** The calculation input from what the buyer typed and the cited readings. */
export function scheduleInput(
  form: ScheduleForm,
  readings: ProgressReading[],
): ScheduleInput {
  return {
    price: enteredNumber(form.price),
    installments: form.rows.map(installment),
    fees: SCHEDULE_FEES,
    loan: form.useLoan
      ? {
          principal: enteredNumber(form.principal),
          annualRatePercent: enteredNumber(form.rate),
          years: enteredNumber(form.years),
        }
      : null,
    progress: readings.map(({ inspectedOn, percent }) => ({
      inspectedOn,
      percent,
    })),
  };
}

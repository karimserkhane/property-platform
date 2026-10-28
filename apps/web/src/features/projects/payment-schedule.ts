/**
 * Payment schedule simulator (C02): pure calculations, no data of its own.
 *
 * The plan, the price and the loan terms are what the buyer enters or what a cited
 * developer document states; fees are either known with their source or unknown,
 * and an unknown fee is never counted as zero. Declared progress comes from dated
 * register readings: a payment is placed against progress only when a reading
 * says so, never by extrapolating the construction curve.
 */

export type Installment =
  | { kind: "on_date"; percent: number; date: string }
  | { kind: "on_progress"; percent: number; progressPercent: number }
  | { kind: "on_handover"; percent: number };

export type FeeSource = { label: string; url: string; consultedOn: string };

export type Fee =
  | {
      id: string;
      status: "known";
      basis: "percent_of_price";
      percent: number;
      source: FeeSource;
    }
  | {
      id: string;
      status: "known";
      basis: "fixed";
      amount: number;
      source: FeeSource;
    }
  | { id: string; status: "unknown" };

export type Loan = {
  principal: number;
  annualRatePercent: number;
  years: number;
};

export type ProgressReading = { inspectedOn: string; percent: number };

export type ScheduleInput = {
  price: number;
  installments: Installment[];
  fees?: Fee[];
  loan?: Loan | null;
  progress?: ProgressReading[];
};

export type ScheduleIssue =
  | "price_invalid"
  | "installment_invalid"
  | "plan_not_100_percent"
  | "fee_invalid"
  | "loan_invalid"
  | "loan_above_price";

const EPSILON = 1e-9;

// Handover is ordered after every construction milestone, 100 % included.
const HANDOVER_THRESHOLD = 101;

const finite = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);

const isDate = (value: unknown): value is string =>
  typeof value === "string" &&
  /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  !Number.isNaN(Date.parse(`${value}T00:00:00Z`));

const isShare = (value: unknown): value is number =>
  finite(value) && value >= 0 && value <= 100;

function installmentValid(installment: Installment) {
  if (!finite(installment.percent)) return false;
  if (installment.percent <= 0 || installment.percent > 100) return false;
  if (installment.kind === "on_date") return isDate(installment.date);
  if (installment.kind === "on_progress")
    return isShare(installment.progressPercent);
  return installment.kind === "on_handover";
}

function feeValid(fee: Fee) {
  if (fee.status === "unknown") return true;
  if (!fee.source?.url || !fee.source.label) return false;
  if (fee.basis === "percent_of_price") return isShare(fee.percent);
  return finite(fee.amount) && fee.amount >= 0;
}

function loanValid(loan: Loan) {
  return (
    finite(loan.principal) &&
    loan.principal > 0 &&
    finite(loan.annualRatePercent) &&
    loan.annualRatePercent >= 0 &&
    Number.isInteger(loan.years) &&
    loan.years > 0
  );
}

/** Readings in date order; unreadable ones are dropped rather than guessed. */
export function orderedReadings(progress: ProgressReading[] = []) {
  return progress
    .filter(
      (reading) => isDate(reading.inspectedOn) && isShare(reading.percent),
    )
    .toSorted((a, b) => a.inspectedOn.localeCompare(b.inspectedOn));
}

/** Latest declared progress on or before a date, or null when none is known. */
export function progressOn(date: string, readings: ProgressReading[]) {
  let found: ProgressReading | null = null;
  for (const reading of readings) {
    if (reading.inspectedOn > date) break;
    found = reading;
  }
  return found;
}

/** First reading at or above a construction milestone, or null if none yet. */
export function milestoneReached(
  progressPercent: number,
  readings: ProgressReading[],
) {
  return (
    readings.find((reading) => reading.percent + EPSILON >= progressPercent) ??
    null
  );
}

/** Level monthly repayment of an annuity loan; a zero rate splits the principal. */
export function monthlyRepayment(loan: Loan) {
  const months = loan.years * 12;
  const rate = loan.annualRatePercent / 100 / 12;
  if (rate === 0) return loan.principal / months;
  return (loan.principal * rate) / (1 - (1 + rate) ** -months);
}

type Placed = {
  installment: Installment;
  threshold: number | null;
  date: string | null;
  // Due strictly after `after` and no later than `by`, from dated readings.
  after: string | null;
  by: string | null;
  declaredProgress: ProgressReading | null;
};

function place(installment: Installment, readings: ProgressReading[]): Placed {
  if (installment.kind === "on_date") {
    // Progress at a date is read from the register, never projected forward.
    return {
      installment,
      threshold: null,
      date: installment.date,
      after: installment.date,
      by: installment.date,
      declaredProgress: progressOn(installment.date, readings),
    };
  }
  const threshold =
    installment.kind === "on_progress"
      ? installment.progressPercent
      : HANDOVER_THRESHOLD;
  // A milestone is due when declared progress reaches it: the first reading at or
  // above it bounds the due date, the last reading below it opens the window.
  // Handover is never read from a percentage, so it has no upper bound.
  const reached =
    installment.kind === "on_progress"
      ? milestoneReached(threshold, readings)
      : null;
  const below = readings.filter(
    (reading) =>
      reading.percent + EPSILON < Math.min(threshold, 100) &&
      (!reached || reading.inspectedOn < reached.inspectedOn),
  );
  return {
    installment,
    threshold,
    date: null,
    after: below.at(-1)?.inspectedOn ?? null,
    by: reached?.inspectedOn ?? null,
    declaredProgress: reached,
  };
}

/** True when `a` is certainly paid no later than `b`. */
function notAfter(a: Placed, b: Placed) {
  if (a === b) return true;
  if (a.threshold !== null && b.threshold !== null)
    return a.threshold <= b.threshold;
  if (a.date !== null && b.date !== null) return a.date <= b.date;
  return a.by !== null && b.after !== null && a.by <= b.after;
}

const sumPercent = (items: Placed[]) =>
  items.reduce((sum, item) => sum + item.installment.percent, 0);

/**
 * The simulated schedule: each payment with its amount, the share of the price
 * paid once it is made and, where a dated reading allows it, the declared progress
 * at that point.
 */
export function simulateSchedule(input: ScheduleInput) {
  const issues = new Set<ScheduleIssue>();
  const fees = input.fees ?? [];
  const loan = input.loan ?? null;
  const readings = orderedReadings(input.progress);

  if (!finite(input.price) || input.price <= 0) issues.add("price_invalid");
  if (!input.installments.every(installmentValid))
    issues.add("installment_invalid");
  if (!fees.every(feeValid)) issues.add("fee_invalid");
  if (loan && !loanValid(loan)) issues.add("loan_invalid");
  if (loan && finite(input.price) && loan.principal > input.price + EPSILON)
    issues.add("loan_above_price");
  if (issues.has("price_invalid") || issues.has("installment_invalid"))
    return { status: "invalid" as const, issues: [...issues] };

  const placed = input.installments.map((installment) =>
    place(installment, readings),
  );
  const planPercent = sumPercent(placed);
  if (Math.abs(planPercent - 100) > EPSILON) issues.add("plan_not_100_percent");

  // A future date and a milestone not yet reached have no known order: the share
  // paid at such a payment is a range, never a guess.
  const payments = placed
    .map((item) => {
      const notLater = placed.filter((other) => notAfter(other, item));
      const strictlyLater = placed.filter(
        (other) => notAfter(item, other) && !notAfter(other, item),
      );
      return {
        installment: item.installment,
        amount: (input.price * item.installment.percent) / 100,
        dueAfter: item.date === null ? item.after : null,
        dueBy: item.by,
        declaredProgress: item.declaredProgress,
        paidPercent: {
          from: sumPercent(notLater),
          to: planPercent - sumPercent(strictlyLater),
        },
      };
    })
    .toSorted(
      (a, b) =>
        a.paidPercent.from - b.paidPercent.from ||
        a.paidPercent.to - b.paidPercent.to,
    );

  const knownFees = fees.flatMap((fee) => {
    if (fee.status !== "known" || !feeValid(fee)) return [];
    const amount =
      fee.basis === "percent_of_price"
        ? (input.price * fee.percent) / 100
        : fee.amount;
    return [{ fee, amount }];
  });
  const unknownFees = fees.filter((fee) => fee.status === "unknown");
  const knownFeesTotal = knownFees.reduce((sum, item) => sum + item.amount, 0);

  let loanResult = null;
  if (loan && !issues.has("loan_invalid") && !issues.has("loan_above_price")) {
    const monthly = monthlyRepayment(loan);
    const totalRepaid = monthly * loan.years * 12;
    loanResult = {
      loan,
      monthlyRepayment: monthly,
      totalRepaid,
      totalInterest: totalRepaid - loan.principal,
    };
  }

  return {
    status: "simulated" as const,
    issues: [...issues],
    price: input.price,
    planPercent,
    payments,
    knownFees,
    unknownFees,
    knownFeesTotal,
    loan: loanResult,
    // A lower bound while any fee is unknown or invalid: never the full cost.
    knownTotalCost:
      input.price + knownFeesTotal + (loanResult?.totalInterest ?? 0),
    totalIsComplete: unknownFees.length === 0 && !issues.has("fee_invalid"),
  };
}

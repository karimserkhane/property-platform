"use client";

import { type ReactNode, useId, useState } from "react";
import { type ScheduleIssue, simulateSchedule } from "./payment-schedule";
import styles from "./schedule.module.css";
import {
  type InstallmentRow,
  type ScheduleForm,
  type ScheduleLabels,
  scheduleInput,
} from "./schedule-form";

const issueKeys: Record<ScheduleIssue, keyof ScheduleLabels> = {
  price_invalid: "priceInvalid",
  installment_invalid: "installmentInvalid",
  plan_not_100_percent: "planNot100",
  fee_invalid: "feeInvalid",
  loan_invalid: "loanInvalid",
  loan_above_price: "loanAbovePrice",
};

type Reading = { inspectedOn: string; percent: number };

/**
 * Payment schedule simulator (C02). The buyer types the price, the plan and the loan;
 * the platform only adds the dated declared progress it can cite, passed in as
 * `readings` (values) and `citations` (the rendered list with its sources).
 */
export function PaymentScheduleSimulator({
  readings,
  citations,
  labels,
  locale,
}: {
  readings: Reading[];
  citations: ReactNode;
  labels: ScheduleLabels;
  locale: string;
}) {
  const id = useId();
  const [next, setNext] = useState(1);
  const [form, setForm] = useState<ScheduleForm>({
    price: "",
    rows: [
      { id: "0", kind: "on_date", percent: "", date: "", progressPercent: "" },
    ],
    useLoan: false,
    principal: "",
    rate: "",
    years: "",
  });
  const result = simulateSchedule(scheduleInput(form, readings));
  const money = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "AED",
    maximumFractionDigits: 0,
  });
  const share = new Intl.NumberFormat(locale, {
    style: "percent",
    maximumFractionDigits: 2,
  });
  const percent = (value: number) => share.format(value / 100);
  const day = (value: string) =>
    new Intl.DateTimeFormat(locale, {
      dateStyle: "medium",
      timeZone: "UTC",
    }).format(new Date(`${value}T00:00:00Z`));
  const update = (patch: Partial<ScheduleForm>) =>
    setForm((current) => ({ ...current, ...patch }));
  const updateRow = (rowId: string, patch: Partial<InstallmentRow>) =>
    setForm((current) => ({
      ...current,
      rows: current.rows.map((row) =>
        row.id === rowId ? { ...row, ...patch } : row,
      ),
    }));
  const addRow = () => {
    setForm((current) => ({
      ...current,
      rows: [
        ...current.rows,
        {
          id: String(next),
          kind: "on_progress",
          percent: "",
          date: "",
          progressPercent: "",
        },
      ],
    }));
    setNext(next + 1);
  };
  const removeRow = (rowId: string) =>
    setForm((current) => ({
      ...current,
      rows: current.rows.filter((row) => row.id !== rowId),
    }));
  // An untouched form asks for the plan rather than listing every missing field.
  const untouched =
    form.price.trim() === "" &&
    form.rows.every((row) => row.percent.trim() === "");
  const issues = untouched
    ? []
    : result.issues.map((issue) => labels[issueKeys[issue]]);

  return (
    <article
      className={styles.simulator}
      aria-labelledby={`${id}-title`}
      data-payment-schedule={result.status}
    >
      <h3 id={`${id}-title`}>{labels.title}</h3>
      <p className={styles.muted}>{labels.intro}</p>
      <form
        className={styles.form}
        onSubmit={(event) => event.preventDefault()}
      >
        <label className={styles.field}>
          <span>{labels.price}</span>
          <input
            type="number"
            inputMode="decimal"
            min="0"
            step="any"
            value={form.price}
            onChange={(event) => update({ price: event.target.value })}
          />
        </label>
        <fieldset className={styles.plan}>
          <legend>{labels.plan}</legend>
          <p className={styles.muted}>{labels.enteredByYou}</p>
          {form.rows.map((row, index) => (
            <div className={styles.row} key={row.id} data-schedule-row>
              <span className={styles.rowNumber}>
                {labels.installment} {index + 1}
              </span>
              <label className={styles.field}>
                <span>{labels.kind}</span>
                <select
                  value={row.kind}
                  onChange={(event) =>
                    updateRow(row.id, {
                      kind: event.target.value as InstallmentRow["kind"],
                    })
                  }
                >
                  <option value="on_date">{labels.onDate}</option>
                  <option value="on_progress">{labels.onProgress}</option>
                  <option value="on_handover">{labels.onHandover}</option>
                </select>
              </label>
              <label className={styles.field}>
                <span>{labels.percent}</span>
                <input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  max="100"
                  step="any"
                  value={row.percent}
                  onChange={(event) =>
                    updateRow(row.id, { percent: event.target.value })
                  }
                />
              </label>
              {row.kind === "on_date" && (
                <label className={styles.field}>
                  <span>{labels.date}</span>
                  <input
                    type="date"
                    value={row.date}
                    onChange={(event) =>
                      updateRow(row.id, { date: event.target.value })
                    }
                  />
                </label>
              )}
              {row.kind === "on_progress" && (
                <label className={styles.field}>
                  <span>{labels.progressPercent}</span>
                  <input
                    type="number"
                    inputMode="decimal"
                    min="0"
                    max="100"
                    step="any"
                    value={row.progressPercent}
                    onChange={(event) =>
                      updateRow(row.id, { progressPercent: event.target.value })
                    }
                  />
                </label>
              )}
              {form.rows.length > 1 && (
                <button
                  type="button"
                  className={styles.remove}
                  onClick={() => removeRow(row.id)}
                >
                  {labels.remove} {index + 1}
                </button>
              )}
            </div>
          ))}
          <button type="button" className={styles.add} onClick={addRow}>
            {labels.add}
          </button>
        </fieldset>
        <fieldset className={styles.plan}>
          <legend>{labels.loan}</legend>
          <label className={styles.check}>
            <input
              type="checkbox"
              checked={form.useLoan}
              onChange={(event) => update({ useLoan: event.target.checked })}
            />
            <span>{labels.useLoan}</span>
          </label>
          {form.useLoan && (
            <div className={styles.row}>
              {(
                [
                  ["principal", labels.principal],
                  ["rate", labels.rate],
                  ["years", labels.years],
                ] as const
              ).map(([key, label]) => (
                <label className={styles.field} key={key}>
                  <span>{label}</span>
                  <input
                    type="number"
                    inputMode="decimal"
                    min="0"
                    step={key === "years" ? "1" : "any"}
                    value={form[key]}
                    onChange={(event) =>
                      update({
                        [key]: event.target.value,
                      } as Partial<ScheduleForm>)
                    }
                  />
                </label>
              ))}
            </div>
          )}
        </fieldset>
      </form>

      <div className={styles.readings}>
        <h4>{labels.readings}</h4>
        {readings.length ? citations : <p>{labels.noReadings}</p>}
      </div>

      <output className={styles.result} aria-live="polite">
        {untouched && <p>{labels.start}</p>}
        {issues.length > 0 && (
          <ul className={styles.issues}>
            {issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        )}
        {result.status === "simulated" && (
          <>
            <h4>{labels.schedule}</h4>
            <ol className={styles.timeline}>
              {result.payments.map((payment, index) => {
                const item = payment.installment;
                const progress = payment.declaredProgress;
                const range = payment.paidPercent;
                const exact = Math.abs(range.to - range.from) < 1e-9;
                return (
                  // biome-ignore lint/suspicious/noArrayIndexKey: payments have no identity beyond their position
                  <li key={index} data-schedule-payment={item.kind}>
                    <p className={styles.when}>
                      {item.kind === "on_date" && (
                        <>
                          {labels.dueOn}{" "}
                          <time dateTime={item.date}>{day(item.date)}</time>
                        </>
                      )}
                      {item.kind === "on_progress" &&
                        `${labels.dueWhenReached} ${percent(item.progressPercent)}`}
                      {item.kind === "on_handover" && labels.dueAtHandover}
                    </p>
                    <p className={styles.amount}>
                      {money.format(payment.amount)} · {percent(item.percent)}
                    </p>
                    {item.kind !== "on_date" && (
                      <p className={styles.muted}>
                        {payment.dueAfter && (
                          <>
                            {labels.dueAfter}{" "}
                            <time dateTime={payment.dueAfter}>
                              {day(payment.dueAfter)}
                            </time>
                            {payment.dueBy ? " · " : ""}
                          </>
                        )}
                        {payment.dueBy ? (
                          <>
                            {labels.dueBy}{" "}
                            <time dateTime={payment.dueBy}>
                              {day(payment.dueBy)}
                            </time>
                          </>
                        ) : item.kind === "on_handover" ? (
                          labels.handoverOpen
                        ) : (
                          labels.notReached
                        )}
                      </p>
                    )}
                    <p className={styles.muted}>
                      {labels.declaredAt}{" "}
                      {progress ? (
                        <>
                          <strong>{percent(progress.percent)}</strong> ·{" "}
                          {labels.inspectedOn}{" "}
                          <time dateTime={progress.inspectedOn}>
                            {day(progress.inspectedOn)}
                          </time>
                        </>
                      ) : (
                        labels.noReadingAtDate
                      )}
                    </p>
                    <p>
                      {labels.paidShare}{" "}
                      <strong>
                        {exact
                          ? percent(range.from)
                          : `${percent(range.from)} – ${percent(range.to)}`}
                      </strong>
                    </p>
                    <div className={styles.bar} aria-hidden="true">
                      <span
                        className={styles.paid}
                        style={{ inlineSize: `${Math.min(range.from, 100)}%` }}
                      />
                      <span
                        className={styles.paidRange}
                        style={{
                          inlineSize: `${Math.max(Math.min(range.to, 100) - Math.min(range.from, 100), 0)}%`,
                        }}
                      />
                      {progress && (
                        <span
                          className={styles.progress}
                          style={{ insetInlineStart: `${progress.percent}%` }}
                        />
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
            <p className={styles.muted}>{labels.barNote}</p>
            {result.payments.some(
              (payment) =>
                Math.abs(payment.paidPercent.to - payment.paidPercent.from) >
                1e-9,
            ) && <p className={styles.muted}>{labels.rangeNote}</p>}
            <dl className={styles.totals}>
              <div>
                <dt>{labels.planTotal}</dt>
                <dd>{percent(result.planPercent)}</dd>
              </div>
              <div>
                <dt>{labels.officialFees}</dt>
                <dd>
                  {labels.unknown}
                  <span className={styles.muted}>
                    {" "}
                    · {labels.officialFeesNote}
                  </span>
                </dd>
              </div>
              {result.loan && (
                <>
                  <div>
                    <dt>{labels.monthly}</dt>
                    <dd>{money.format(result.loan.monthlyRepayment)}</dd>
                  </div>
                  <div>
                    <dt>{labels.interest}</dt>
                    <dd>{money.format(result.loan.totalInterest)}</dd>
                  </div>
                </>
              )}
              <div>
                <dt>{labels.totalKnown}</dt>
                <dd className={styles.total}>
                  {money.format(result.knownTotalCost)}
                </dd>
                <dd className={styles.muted}>
                  {result.totalIsComplete
                    ? labels.totalComplete
                    : labels.totalLowerBound}
                </dd>
              </div>
            </dl>
          </>
        )}
      </output>
      <p className={styles.muted}>{labels.notAdvice}</p>
    </article>
  );
}

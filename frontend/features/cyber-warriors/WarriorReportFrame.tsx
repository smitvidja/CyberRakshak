"use client";

import type {ReactNode} from "react";
import {CheckCircle2, ShieldCheck} from "lucide-react";
import {useTranslations} from "next-intl";

export type ReportStep = 1 | 2 | 3 | 4;

export function WarriorReportFrame({activeStep, children}: {activeStep: ReportStep; children: ReactNode}) {
  const t = useTranslations("warriorReport");
  const steps = [
    {copy: t("stepIdentifyCopy"), title: t("stepIdentify")},
    {copy: t("stepDescribeCopy"), title: t("stepDescribe")},
    {copy: t("stepEvidenceCopy"), title: t("stepEvidence")},
    {copy: t("stepReviewCopy"), title: t("stepReview")}
  ];

  return (
    <main className="warrior-page warrior-application-page">
      <div className="shell-container warrior-application-layout">
        <aside className="warrior-application-rail" aria-label={t("stepsLabel")}>
          <p className="warrior-step-label">{t("reportTitle")}</p>
          <h1>{t("reportSubtitle")}</h1>
          <ol>
            {steps.map((step, index) => {
              const position = (index + 1) as ReportStep;
              const complete = activeStep > position;
              return (
                <li className={activeStep === position ? "is-active" : complete ? "is-complete" : ""} key={step.title}>
                  <span aria-hidden="true">{complete ? <CheckCircle2 size={18} /> : position}</span>
                  <div><strong>{step.title}</strong><small>{step.copy}</small></div>
                </li>
              );
            })}
          </ol>
          <div className="warrior-application-rail-note">
            <ShieldCheck aria-hidden="true" size={20} />
            <span>{t("privacyNote")}</span>
          </div>
        </aside>
        <section className="warrior-application-workspace">{children}</section>
      </div>
    </main>
  );
}

export function ReportHeading({eyebrow, title, copy}: {eyebrow: string; copy: string; title: string}) {
  return <header className="warrior-application-heading"><span>{eyebrow}</span><h2>{title}</h2><p>{copy}</p></header>;
}

export function ReportError({message}: {message: string}) {
  return message ? <div className="warrior-application-error" role="alert">{message}</div> : null;
}

"use client";

import type {ReactNode} from "react";
import {CheckCircle2, FileText, Info, ListChecks, ShieldCheck} from "lucide-react";
import {useTranslations} from "next-intl";

type ApplicationStep = 1 | 2 | 3;

export function WarriorApplicationFrame({
  activeStep,
  children,
  notice
}: {
  activeStep: ApplicationStep;
  children: ReactNode;
  notice?: ReactNode;
}) {
  const t = useTranslations("warriorApplication");
  const steps = [
    {icon: FileText, title: t("stepUpload"), copy: t("stepUploadCopy")},
    {icon: ListChecks, title: t("stepDetails"), copy: t("stepDetailsCopy")},
    {icon: ShieldCheck, title: t("stepReview"), copy: t("stepReviewCopy")}
  ];

  return (
    <main className="warrior-page warrior-application-page">
      <div className="shell-container warrior-application-layout">
        <aside className="warrior-application-rail" aria-label={t("stepsLabel")}>
          <p className="warrior-step-label">{t("applicationSteps")}</p>
          <h1>{t("applicationTitle")}</h1>
          <ol>
            {steps.map((step, index) => {
              const position = (index + 1) as ApplicationStep;
              const Icon = step.icon;
              const complete = activeStep > position;
              return (
                <li className={activeStep === position ? "is-active" : complete ? "is-complete" : ""} key={step.title}>
                  <span aria-hidden="true">{complete ? <CheckCircle2 size={18} /> : <Icon size={18} />}</span>
                  <div><strong>{step.title}</strong><small>{step.copy}</small></div>
                </li>
              );
            })}
          </ol>
          <div className="warrior-application-rail-note">
            <Info aria-hidden="true" size={20} />
            <span>{t("reviewRequiredNote")}</span>
          </div>
        </aside>
        <section className="warrior-application-workspace">{children}</section>
      </div>
      <div className="shell-container warrior-session-notice">
        <ShieldCheck aria-hidden="true" size={19} />
        <strong>{t("privacyTitle")}</strong>
        <span>{notice ?? t("privacyCopy")}</span>
      </div>
    </main>
  );
}

export function ApplicationHeading({eyebrow, title, copy}: {eyebrow: string; title: string; copy: string}) {
  return <header className="warrior-application-heading"><span>{eyebrow}</span><h2>{title}</h2><p>{copy}</p></header>;
}

export function ApplicationError({message}: {message: string}) {
  return message ? <div className="warrior-application-error" role="alert">{message}</div> : null;
}

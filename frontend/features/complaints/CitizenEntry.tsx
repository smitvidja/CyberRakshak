"use client";

import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";

import {authApi} from "@/lib/api/auth";
import {usersApi} from "@/lib/api/users";
import {getAccessToken, getReportMode, setAccessToken, setReportCategoryHint, setReportMode} from "@/lib/auth/citizen-session";
import {Button} from "@/components/ui/Button";
import {TextInput} from "@/components/ui/FormFields";
import {StatePanel, SurfaceCard} from "@/components/ui/Surface";

const dashboardPath = (locale: string) => `/${locale}/report-crime/dashboard`;
const permitsAnonymousReporting = (category: string | null) => category === "women" || category === "women-child";

export function ReportTypeChoice() {
  const t = useTranslations("citizenEntry");
  const locale = useLocale();
  const router = useRouter();
  const [category, setCategory] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const nextCategory = params.get("category");
    const mode = params.get("mode");
    setCategory(nextCategory);

    if (nextCategory) setReportCategoryHint(nextCategory);
    if (mode !== "anonymous" && mode !== "identified") return;

    if (mode === "anonymous" && !permitsAnonymousReporting(nextCategory)) {
      setReportMode("identified");
      router.replace(`/${locale}/report-crime/verify`);
      return;
    }

    setReportMode(mode);
    router.replace(mode === "anonymous" ? dashboardPath(locale) : `/${locale}/report-crime/verify`);
  }, [locale, router]);

  function chooseAnonymous() {
    if (!permitsAnonymousReporting(category)) return;
    setReportMode("anonymous");
    router.push(dashboardPath(locale));
  }

  function chooseIdentified() {
    setReportMode("identified");
    router.push(`/${locale}/report-crime/verify`);
  }

  const allowAnonymous = permitsAnonymousReporting(category);

  return (
    <main className="citizen-page citizen-entry-page bg-[#f3f7fb] py-7 sm:py-10">
      <div className="shell-container mx-auto max-w-6xl">
        <header className="citizen-page-heading border-l-4 border-[#075fb9] bg-white px-6 py-6 shadow-[0_2px_9px_rgb(15_42_74_/_0.08)] sm:px-8">
          <p className="eyebrow">{t("eyebrow")}</p>
          <h1 className="mt-2 text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("title")}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)] sm:text-base">{t("intro")}</p>
        </header>
        <div className="citizen-safety-note mt-4 border border-[#abd2f5] bg-[#f7fbff] px-5 py-4 text-[#07529d]"><strong className="block text-sm">{t("noticeTitle")}</strong><p className="mt-1 text-sm leading-6">{t("noticeCopy")}</p></div>
        <div className={allowAnonymous ? "mt-5 grid gap-4 md:grid-cols-2" : "mt-5 max-w-3xl"}>
          {allowAnonymous ? <section className="citizen-route-card border-t-4 border-t-[#075fb9] bg-white p-6 shadow-[0_3px_12px_rgb(15_42_74_/_0.08)]"><div className="flex items-start gap-4"><span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[#eaf4ff] text-sm font-bold text-[#075bbf]">01</span><div><h2 className="text-xl font-bold text-[var(--navy)]">{t("anonymousTitle")}</h2><p className="mt-2 text-sm leading-6 text-[var(--muted)]">{t("anonymousCopy")}</p></div></div><ul className="mt-5 space-y-2 border-t border-[var(--border)] pt-4 text-sm leading-6 text-[var(--ink)]"><li>{t("anonymousPointOne")}</li><li>{t("anonymousPointTwo")}</li></ul><Button className="mt-6 w-full sm:w-auto" onClick={chooseAnonymous}>{t("anonymousAction")}</Button></section> : null}
          <section className="citizen-route-card border-t-4 border-t-[#8dbde9] bg-white p-6 shadow-[0_3px_12px_rgb(15_42_74_/_0.08)]"><div className="flex items-start gap-4"><span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[#edf6ff] text-sm font-bold text-[#075bbf]">{allowAnonymous ? "02" : "01"}</span><div><h2 className="text-xl font-bold text-[var(--navy)]">{t("identifiedTitle")}</h2><p className="mt-2 text-sm leading-6 text-[var(--muted)]">{t("identifiedCopy")}</p></div></div><ul className="mt-5 space-y-2 border-t border-[var(--border)] pt-4 text-sm leading-6 text-[var(--ink)]"><li>{t("identifiedPointOne")}</li><li>{t("identifiedPointTwo")}</li></ul><Button className="mt-6 w-full sm:w-auto" onClick={chooseIdentified} variant="outline">{t("identifiedAction")}</Button></section>
        </div>
      </div>
    </main>
  );
}

export function MockIdentityForm() {
  const t = useTranslations("citizenEntry");
  const locale = useLocale();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(formData: FormData) {
    setLoading(true);
    setError("");
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");
    const payload = {email, password, phone: String(formData.get("phone") ?? ""), role: "CITIZEN"};
    const registration = await authApi.register(payload);
    if (!registration.ok && registration.error.code !== "CONFLICT") { setError(t("profileError")); setLoading(false); return; }
    const login = await authApi.login({email, password});
    if (!login.ok) { setError(t("profileError")); setLoading(false); return; }
    setAccessToken(login.data.access_token);
    const saved = await usersApi.saveMyProfile({full_name: String(formData.get("fullName") ?? ""), city: String(formData.get("city") ?? "") || null, state: String(formData.get("state") ?? "") || null}, {accessToken: login.data.access_token});
    if (!saved.ok) { setError(t("profileError")); setLoading(false); return; }
    setReportMode("identified");
    router.push(dashboardPath(locale));
  }

  return <main className="citizen-page shell-container py-8 sm:py-12"><div className="citizen-form-layout mx-auto grid max-w-6xl gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
    <section><p className="eyebrow">{t("identifiedEyebrow")}</p><h1 className="mt-2 text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("profileTitle")}</h1><p className="mt-3 max-w-2xl text-base leading-7 text-[var(--muted)]">{t("identifiedCopy")}</p><StatePanel title={t("mockTitle")} tone="warning">{t("mockCopy")}</StatePanel><form action={submit} className="mt-6 space-y-5"><SurfaceCard heading={t("profileTitle")}><div className="grid gap-5 sm:grid-cols-2"><TextInput id="fullName" label={t("fullName")} required name="fullName" /><TextInput id="phone" label={t("phone")} name="phone" type="tel" /><TextInput id="email" label={t("email")} required name="email" type="email" /><TextInput id="password" label={t("password")} required name="password" type="password" minLength={8} /><TextInput id="city" label={t("city")} name="city" /><TextInput id="state" label={t("state")} name="state" /></div>{error ? <p className="mt-4 text-sm font-bold text-[var(--danger)]" role="alert">{error}</p> : null}<Button className="mt-7 w-full sm:w-auto" isLoading={loading} type="submit">{t("profileAction")}</Button></SurfaceCard></form></section>
    <aside className="citizen-progress-rail self-start rounded-[8px] border border-[#c9def2] bg-white p-5 shadow-[0_2px_9px_rgb(15_42_74_/_0.08)]"><h2 className="text-base font-bold text-[var(--navy)]">{t("dashboardEyebrow")}</h2><ol className="mt-5 space-y-4"><li className="flex gap-3"><span>1</span><div><strong>{t("profileTitle")}</strong><p>{t("identifiedCopy")}</p></div></li><li className="flex gap-3"><span>2</span><div><strong>{t("stepOne")}</strong><p>{t("stepOneCopy")}</p></div></li><li className="flex gap-3"><span>3</span><div><strong>{t("stepThree")}</strong><p>{t("stepThreeCopy")}</p></div></li></ol></aside>
  </div></main>;
}

export function CitizenStartState() {
  const t = useTranslations("citizenEntry");
  const locale = useLocale();
  const router = useRouter();
  const [identified, setIdentified] = useState(false);
  useEffect(() => { setIdentified(getReportMode() === "identified" && Boolean(getAccessToken())); }, []);
  const steps = [{title: t("stepOne"), copy: t("stepOneCopy")}, {title: t("stepTwo"), copy: t("stepTwoCopy")}, {title: t("stepThree"), copy: t("stepThreeCopy")}];
  return <main className="citizen-page shell-container py-8 sm:py-12"><div className="mx-auto max-w-6xl"><div className="citizen-dashboard-intro"><div><p className="eyebrow">{t("dashboardEyebrow")}</p><h1 className="mt-2 text-3xl font-bold text-[var(--navy)] sm:text-4xl">{identified ? t("identifiedReadyTitle") : t("anonymousReadyTitle")}</h1><p className="mt-3 max-w-3xl text-base leading-7 text-[var(--muted)]">{identified ? t("identifiedReadyCopy") : t("anonymousReadyCopy")}</p></div><Button onClick={() => router.push(`/${locale}/report-crime/new/incident`)}>{t("startIncident")}</Button></div><div className="mt-6 grid gap-4 md:grid-cols-3">{steps.map((step, index) => <SurfaceCard key={step.title} className="citizen-dashboard-card" heading={<span className="flex items-center gap-3"><span className="grid h-8 w-8 place-items-center rounded-full bg-[#eaf4ff] text-xs font-bold text-[#075bbf]">0{index + 1}</span>{step.title}</span>}><p className="text-sm leading-6 text-[var(--muted)]">{step.copy}</p></SurfaceCard>)}</div><StatePanel action={<Button onClick={() => router.push(`/${locale}/report-crime/new/incident`)}>{t("startIncident")}</Button>} title={t("nextTitle")} tone="success">{t("nextCopy")}</StatePanel></div></main>;
}
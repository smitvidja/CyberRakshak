"use client";

import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";

import {authApi} from "@/lib/api/auth";
import {usersApi} from "@/lib/api/users";
import {getAccessToken, getReportMode, setAccessToken, setReportMode} from "@/lib/auth/citizen-session";
import {Button} from "@/components/ui/Button";
import {TextInput} from "@/components/ui/FormFields";
import {StatePanel, SurfaceCard} from "@/components/ui/Surface";

const dashboardPath = (locale: string) => "/" + locale + "/report-crime/dashboard";

export function ReportTypeChoice() {
  const t = useTranslations("citizenEntry");
  const locale = useLocale();
  const router = useRouter();

  function chooseAnonymous() {
    setReportMode("anonymous");
    router.push(dashboardPath(locale));
  }

  function chooseIdentified() {
    setReportMode("identified");
    router.push("/" + locale + "/report-crime/verify");
  }

  return <main className="shell-container py-8 sm:py-12"><div className="mx-auto max-w-5xl"><p className="eyebrow">{t("eyebrow")}</p><h1 className="mt-2 text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("title")}</h1><p className="mt-3 max-w-3xl text-base leading-7 text-[var(--muted)]">{t("intro")}</p><StatePanel title={t("noticeTitle")} tone="info">{t("noticeCopy")}</StatePanel><div className="mt-6 grid gap-5 md:grid-cols-2"><SurfaceCard heading={t("anonymousTitle")}><p className="text-sm leading-6 text-[var(--muted)]">{t("anonymousCopy")}</p><ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-[var(--ink)]"><li>{t("anonymousPointOne")}</li><li>{t("anonymousPointTwo")}</li></ul><Button className="mt-6 w-full" onClick={chooseAnonymous}>{t("anonymousAction")}</Button></SurfaceCard><SurfaceCard heading={t("identifiedTitle")}><p className="text-sm leading-6 text-[var(--muted)]">{t("identifiedCopy")}</p><ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-[var(--ink)]"><li>{t("identifiedPointOne")}</li><li>{t("identifiedPointTwo")}</li></ul><Button className="mt-6 w-full" onClick={chooseIdentified} variant="outline">{t("identifiedAction")}</Button></SurfaceCard></div></div></main>;
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

  return <main className="shell-container py-8 sm:py-12"><div className="mx-auto max-w-2xl"><p className="eyebrow">{t("identifiedEyebrow")}</p><h1 className="mt-2 text-3xl font-bold text-[var(--navy)]">{t("profileTitle")}</h1><StatePanel title={t("mockTitle")} tone="warning">{t("mockCopy")}</StatePanel><form action={submit} className="mt-6 space-y-5"><SurfaceCard heading={t("profileTitle")}><div className="grid gap-4 sm:grid-cols-2"><TextInput id="fullName" label={t("fullName")} required name="fullName" /><TextInput id="phone" label={t("phone")} name="phone" type="tel" /><TextInput id="email" label={t("email")} required name="email" type="email" /><TextInput id="password" label={t("password")} required name="password" type="password" minLength={8} /><TextInput id="city" label={t("city")} name="city" /><TextInput id="state" label={t("state")} name="state" /></div>{error ? <p className="mt-4 text-sm font-bold text-[var(--danger)]" role="alert">{error}</p> : null}<Button className="mt-6 w-full sm:w-auto" isLoading={loading} type="submit">{t("profileAction")}</Button></SurfaceCard></form></div></main>;
}

export function CitizenStartState() {
  const t = useTranslations("citizenEntry");
  const locale = useLocale();
  const [identified, setIdentified] = useState(false);
  useEffect(() => {
    setIdentified(getReportMode() === "identified" && Boolean(getAccessToken()));
  }, []);
  return <main className="shell-container py-8 sm:py-12"><div className="mx-auto max-w-4xl"><p className="eyebrow">{t("dashboardEyebrow")}</p><h1 className="mt-2 text-3xl font-bold text-[var(--navy)]">{identified ? t("identifiedReadyTitle") : t("anonymousReadyTitle")}</h1><p className="mt-3 text-base leading-7 text-[var(--muted)]">{identified ? t("identifiedReadyCopy") : t("anonymousReadyCopy")}</p><div className="mt-6 grid gap-4 sm:grid-cols-3"><SurfaceCard heading={t("stepOne")}><p className="text-sm leading-6 text-[var(--muted)]">{t("stepOneCopy")}</p></SurfaceCard><SurfaceCard heading={t("stepTwo")}><p className="text-sm leading-6 text-[var(--muted)]">{t("stepTwoCopy")}</p></SurfaceCard><SurfaceCard heading={t("stepThree")}><p className="text-sm leading-6 text-[var(--muted)]">{t("stepThreeCopy")}</p></SurfaceCard></div><StatePanel action={<Button onClick={() => location.assign("/" + locale + "/report-crime")}>{t("chooseAgain")}</Button>} title={t("nextTitle")} tone="success">{t("nextCopy")}</StatePanel></div></main>;
}

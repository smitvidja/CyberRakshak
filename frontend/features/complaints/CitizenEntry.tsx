"use client";

import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";

import {authApi, type MockIdentityProfile} from "@/lib/api/auth";
import {usersApi} from "@/lib/api/users";
import {getAccessToken, getMockIdentityProfile, getReportMode, setAccessToken, setMockIdentityProfile, setReportCategoryHint, setReportMode} from "@/lib/auth/citizen-session";
import {Button} from "@/components/ui/Button";
import {TextInput} from "@/components/ui/FormFields";
import {StatePanel, SurfaceCard} from "@/components/ui/Surface";

const dashboardPath = (locale: string) => `/${locale}/report-crime/dashboard`;
const profilePath = (locale: string) => `/${locale}/report-crime/profile`;
const permitsAnonymousReporting = (category: string | null) => category === "women" || category === "women-child";

type ProfileForm = Omit<MockIdentityProfile, "age" | "registered_mobile"> & {alternate_phone: string};

function profileFormFrom(profile: MockIdentityProfile): ProfileForm {
  return {
    address: profile.address,
    alternate_phone: "",
    city: profile.city,
    date_of_birth: profile.date_of_birth,
    full_name: profile.full_name,
    gender: profile.gender,
    postal_code: profile.postal_code,
    state: profile.state
  };
}

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
  const [demoIdentityId, setDemoIdentityId] = useState("");
  const [otp, setOtp] = useState("");
  const [maskedMobile, setMaskedMobile] = useState("");
  const [step, setStep] = useState<"identity" | "otp">("identity");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function requestOtp(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const result = await authApi.requestMockIdentityOtp({demo_identity_id: demoIdentityId});
    if (!result.ok) {
      setError(t("identityRequestError"));
      setLoading(false);
      return;
    }
    setMaskedMobile(result.data.masked_mobile);
    setStep("otp");
    setLoading(false);
  }

  async function verifyOtp(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const result = await authApi.verifyMockIdentityOtp({demo_identity_id: demoIdentityId, otp});
    if (!result.ok) {
      setError(t("identityVerifyError"));
      setLoading(false);
      return;
    }
    setAccessToken(result.data.access_token);
    setMockIdentityProfile(result.data.profile);
    setReportMode("identified");
    router.push(profilePath(locale));
  }

  return <main className="citizen-page shell-container py-8 sm:py-12"><div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(300px,1.05fr)]">
    <section className="space-y-5"><p className="eyebrow">{t("identityEyebrow")}</p><h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("identityTitle")}</h1><p className="max-w-xl text-base leading-7 text-[var(--muted)]">{t("identityIntro")}</p><StatePanel title={t("mockTitle")} tone="warning">{t("mockIdentityCopy")}</StatePanel>
      <SurfaceCard heading={step === "identity" ? t("identityCardTitle") : t("otpCardTitle")}>
        {step === "identity" ? <form className="space-y-5" onSubmit={requestOtp}><TextInput description={t("identityInputHelp")} id="demo-identity-id" label={t("identityId")} onChange={(event) => setDemoIdentityId(event.target.value.toUpperCase())} placeholder="DEMO-AADHAAR-RAHUL" required value={demoIdentityId} />{error ? <p className="text-sm font-bold text-[var(--danger)]" role="alert">{error}</p> : null}<Button className="w-full sm:w-auto" isLoading={loading} type="submit">{t("sendOtp")}</Button></form> : <form className="space-y-5" onSubmit={verifyOtp}><StatePanel title={t("otpIssuedTitle")} tone="info">{t("otpIssuedCopy", {mobile: maskedMobile})}</StatePanel><TextInput id="demo-otp" inputMode="numeric" label={t("otpLabel")} maxLength={6} onChange={(event) => setOtp(event.target.value.replace(/\D/g, ""))} pattern="[0-9]{6}" required value={otp} />{error ? <p className="text-sm font-bold text-[var(--danger)]" role="alert">{error}</p> : null}<div className="flex flex-wrap gap-3"><Button isLoading={loading} type="submit">{t("verifyContinue")}</Button><Button onClick={() => { setStep("identity"); setOtp(""); setError(""); }} variant="outline">{t("changeIdentity")}</Button></div></form>}
      </SurfaceCard>
    </section>
    <aside className="self-start rounded-[8px] border border-[#c9def2] bg-white p-6 shadow-[0_3px_12px_rgb(15_42_74_/_0.08)]"><p className="text-sm font-bold uppercase tracking-[0.08em] text-[#075bbf]">{t("demoCredentialsEyebrow")}</p><h2 className="mt-2 text-xl font-bold text-[var(--navy)]">{t("demoCredentialsTitle")}</h2><p className="mt-2 text-sm leading-6 text-[var(--muted)]">{t("demoCredentialsCopy")}</p><dl className="mt-5 space-y-3"><div className="rounded-[6px] border border-[#d9e8f7] bg-[#f8fbff] p-4"><dt className="text-xs font-bold uppercase tracking-[0.08em] text-[#426183]">{t("demoOne")}</dt><dd className="mt-2 font-mono text-sm font-bold text-[#083a7d]">DEMO-AADHAAR-RAHUL</dd><dd className="mt-1 text-sm text-[var(--ink)]">OTP: 123456</dd></div><div className="rounded-[6px] border border-[#d9e8f7] bg-[#f8fbff] p-4"><dt className="text-xs font-bold uppercase tracking-[0.08em] text-[#426183]">{t("demoTwo")}</dt><dd className="mt-2 font-mono text-sm font-bold text-[#083a7d]">DEMO-AADHAAR-ANANYA</dd><dd className="mt-1 text-sm text-[var(--ink)]">OTP: 654321</dd></div></dl></aside>
  </div></main>;
}

export function VerifiedProfileReview() {
  const t = useTranslations("citizenEntry");
  const locale = useLocale();
  const router = useRouter();
  const [profile, setProfile] = useState<MockIdentityProfile | null>(null);
  const [form, setForm] = useState<ProfileForm | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const stored = getMockIdentityProfile();
    if (!stored || !getAccessToken()) {
      router.replace(`/${locale}/report-crime/verify`);
      return;
    }
    setProfile(stored);
    setForm(profileFormFrom(stored));
  }, [locale, router]);

  if (!profile || !form) return <main className="citizen-page shell-container py-8 sm:py-12"><StatePanel title={t("profileLoadingTitle")} tone="loading">{t("profileLoadingCopy")}</StatePanel></main>;

  function update(field: keyof ProfileForm, value: string) { setForm((current) => current ? {...current, [field]: value} : current); }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const accessToken = getAccessToken();
    const currentForm = form;
    const currentProfile = profile;
    if (!accessToken || !currentForm || !currentProfile) return;
    setLoading(true);
    setError("");
    const result = await usersApi.saveMyProfile({...currentForm, alternate_phone: currentForm.alternate_phone || null}, {accessToken});
    if (!result.ok) {
      setError(t("profileError"));
      setLoading(false);
      return;
    }
    setMockIdentityProfile({...currentProfile, ...currentForm, age: typeof result.data.age === "number" ? result.data.age : currentProfile.age, registered_mobile: typeof result.data.registered_mobile === "string" ? result.data.registered_mobile : currentProfile.registered_mobile});
    router.push(dashboardPath(locale));
  }

  return <main className="citizen-page shell-container py-8 sm:py-12"><div className="mx-auto max-w-6xl"><p className="eyebrow">{t("profileEyebrow")}</p><h1 className="mt-2 text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("profileReviewTitle")}</h1><p className="mt-3 max-w-3xl text-base leading-7 text-[var(--muted)]">{t("profileReviewCopy")}</p><StatePanel title={t("profileVerifiedTitle")} tone="success">{t("profileVerifiedCopy")}</StatePanel><form className="mt-6" onSubmit={save}><SurfaceCard heading={t("profileDetailsTitle")}><div className="grid gap-5 sm:grid-cols-2"><TextInput id="profile-full-name" label={t("fullName")} readOnly value={form.full_name} /><TextInput id="profile-primary-mobile" label={t("registeredMobile")} readOnly value={profile.registered_mobile} /><TextInput id="profile-dob" label={t("dateOfBirth")} onChange={(event) => update("date_of_birth", event.target.value)} type="date" value={form.date_of_birth} /><TextInput id="profile-age" label={t("age")} readOnly value={String(profile.age)} /><TextInput id="profile-gender" label={t("gender")} onChange={(event) => update("gender", event.target.value)} value={form.gender} /><TextInput id="profile-alternate-mobile" label={t("alternateMobile")} onChange={(event) => update("alternate_phone", event.target.value)} type="tel" value={form.alternate_phone} /><div className="sm:col-span-2"><TextInput id="profile-address" label={t("address")} onChange={(event) => update("address", event.target.value)} value={form.address} /></div><TextInput id="profile-city" label={t("city")} onChange={(event) => update("city", event.target.value)} value={form.city} /><TextInput id="profile-state" label={t("state")} onChange={(event) => update("state", event.target.value)} value={form.state} /><TextInput id="profile-postal" label={t("postalCode")} onChange={(event) => update("postal_code", event.target.value)} value={form.postal_code} /></div>{error ? <p className="mt-4 text-sm font-bold text-[var(--danger)]" role="alert">{error}</p> : null}<div className="mt-7 flex flex-wrap justify-end gap-3"><Button onClick={() => router.push(dashboardPath(locale))} variant="outline">{t("goDashboard")}</Button><Button isLoading={loading} type="submit">{t("saveProfile")}</Button></div></SurfaceCard></form></div></main>;
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
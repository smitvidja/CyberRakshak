"use client";

import Image from "next/image";
import Link from "next/link";
import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Binoculars,
  Check,
  CheckCircle2,
  ClipboardCheck,
  FileSearch,
  Fingerprint,
  Gavel,
  LockKeyhole,
  Medal,
  ScanSearch,
  ShieldCheck,
  Smartphone,
  UsersRound
} from "lucide-react";

import {Button} from "@/components/ui/Button";
import {SelectField, TextInput} from "@/components/ui/FormFields";
import {StatePanel} from "@/components/ui/Surface";
import {authApi, type MockIdentityProfile} from "@/lib/api/auth";
import {cyberWarriorsApi, warriorApplicationsApi} from "@/lib/api/cyber-warriors";
import {
  getWarriorIdentity,
  getWarriorToken,
  setWarriorIdentity,
  setWarriorProfileSetup,
  setWarriorToken
} from "@/lib/auth/warrior-session";

const warriorPath = (locale: string) => `/${locale}/cyber-warrior`;
const verifyPath = (locale: string) => `${warriorPath(locale)}/verify`;
const profilePath = (locale: string) => `${verifyPath(locale)}/profile`;
const applicationPath = (locale: string) => `${warriorPath(locale)}/apply`;
const dashboardPath = (locale: string) => `${warriorPath(locale)}/dashboard`;

const dutyIcons = [Binoculars, ClipboardCheck, UsersRound, Gavel, Medal] as const;

export function WarriorLanding() {
  const t = useTranslations("warriorOnboarding");
  const locale = useLocale();
  const duties = [1, 2, 3, 4, 5].map((number, index) => ({
    copy: t(`duty${number}Copy`),
    icon: dutyIcons[index],
    title: t(`duty${number}Title`)
  }));

  return (
    <main className="warrior-page warrior-landing-page">
      <section className="warrior-landing-hero shell-container">
        <div className="warrior-landing-copy">
          <p className="eyebrow">{t("landingEyebrow")}</p>
          <h1>{t("landingTitle")}</h1>
          <p className="warrior-landing-subtitle">{t("landingSubtitle")}</p>
          <p className="warrior-landing-description">{t("landingCopy")}</p>
          <div className="warrior-landing-actions">
            <Link className="portal-primary-link" href={verifyPath(locale)}>
              <UsersRound aria-hidden="true" size={19} />
              {t("applyAction")}
              <ArrowRight aria-hidden="true" size={18} />
            </Link>
            <a className="warrior-text-link" href="#warrior-duties">
              <FileSearch aria-hidden="true" size={17} />
              {t("learnAction")}
            </a>
          </div>
        </div>

        <div className="warrior-landing-media" aria-label={t("heroImageLabel")}>
          <Image
            alt={t("heroImageAlt")}
            className="warrior-landing-image"
            fill
            priority
            sizes="(max-width: 900px) 100vw, 52vw"
            src="/images/home/cyber-safety-hero.png"
          />
          <div className="warrior-media-shade" />
          <div className="warrior-media-callout warrior-media-callout-top">
            <ScanSearch aria-hidden="true" size={24} />
            <span>{t("spotActivity")}</span>
          </div>
          <div className="warrior-media-callout warrior-media-callout-bottom">
            <ShieldCheck aria-hidden="true" size={24} />
            <span>{t("helpSafely")}</span>
          </div>
          <div className="warrior-media-caption">
            <ShieldCheck aria-hidden="true" size={35} />
            <strong>{t("volunteerOnlyTitle")}</strong>
            <span>{t("volunteerOnlyCopy")}</span>
          </div>
        </div>
      </section>

      <section className="warrior-duties shell-container" id="warrior-duties">
        <div className="warrior-section-heading">
          <span />
          <div>
            <h2>{t("dutiesTitle")}</h2>
            <p>{t("dutiesCopy")}</p>
          </div>
          <span />
        </div>
        <div className="warrior-duty-grid">
          {duties.map(({copy, icon: Icon, title}, index) => (
            <article className="warrior-duty" key={title}>
              <span className="warrior-duty-icon" aria-hidden="true"><Icon size={28} /></span>
              <h3>{index + 1}. {title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
        <div className="warrior-important-note">
          <ShieldCheck aria-hidden="true" size={21} />
          <p><strong>{t("importantLabel")}</strong> {t("importantCopy")}</p>
        </div>
      </section>
    </main>
  );
}

export function WarriorIdentityVerification() {
  const t = useTranslations("warriorOnboarding");
  const locale = useLocale();
  const router = useRouter();
  const [identityId, setIdentityId] = useState("");
  const [otp, setOtp] = useState("");
  const [maskedMobile, setMaskedMobile] = useState("");
  const [requesting, setRequesting] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [requestError, setRequestError] = useState("");
  const [verifyError, setVerifyError] = useState("");

  async function requestOtp(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedIdentity = identityId.replace(/\D/g, "");
    if (!/^\d{14}$/.test(normalizedIdentity)) {
      setRequestError(t("identityValidation"));
      return;
    }
    setRequesting(true);
    setRequestError("");
    setVerifyError("");
    const result = await authApi.requestMockIdentityOtp({demo_identity_id: normalizedIdentity});
    if (!result.ok) {
      setRequestError(t("identityRequestError"));
      setRequesting(false);
      return;
    }
    setIdentityId(normalizedIdentity);
    setMaskedMobile(result.data.masked_mobile);
    setOtp("");
    setRequesting(false);
  }

  async function verifyOtp(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!/^\d{6}$/.test(otp)) {
      setVerifyError(t("otpValidation"));
      return;
    }
    setVerifying(true);
    setVerifyError("");
    const verified = await authApi.verifyMockIdentityOtp({
      demo_identity_id: identityId,
      otp,
      role: "CYBER_WARRIOR"
    });
    if (!verified.ok) {
      setVerifyError(t("identityVerifyError"));
      setVerifying(false);
      return;
    }
    const current = await authApi.current({accessToken: verified.data.access_token});
    const accountEmail = current.ok && typeof current.data.email === "string"
      ? current.data.email
      : "warrior@cyberrakshak.example.com";
    setWarriorToken(verified.data.access_token);
    setWarriorIdentity({
      accountEmail,
      demoIdentityId: identityId,
      profile: verified.data.profile
    });

    // A returning warrior (one who already has at least one application on file) is signing
    // back in, not registering for the first time - send them straight to their dashboard
    // instead of re-running the profile-setup/apply wizard on every verification.
    const existingApplications = await warriorApplicationsApi.listMine({accessToken: verified.data.access_token});
    if (existingApplications.ok && existingApplications.data.length > 0) {
      router.push(dashboardPath(locale));
      return;
    }

    router.push(profilePath(locale));
  }

  return (
    <main className="warrior-page shell-container py-7 sm:py-10">
      <section className="warrior-identity-layout">
        <div className="warrior-identity-form-panel">
          <p className="warrior-step-label">{t("verifyStep")}</p>
          <h1>{t("verifyTitle")}</h1>
          <p className="warrior-form-intro">{t("verifyIntro")}</p>

          <form className="mt-7 space-y-5" onSubmit={requestOtp}>
            <TextInput
              autoComplete="off"
              description={t("identityHelp")}
              error={requestError}
              id="warrior-demo-identity"
              inputMode="numeric"
              label={t("identityLabel")}
              maxLength={14}
              onChange={(event) => setIdentityId(event.target.value.replace(/\D/g, ""))}
              placeholder={t("identityPlaceholder")}
              required
              value={identityId}
            />
            <div className="warrior-data-note">
              <ShieldCheck aria-hidden="true" size={20} />
              <span>{t("syntheticNotice")}</span>
            </div>
            <Button className="w-full" isLoading={requesting} size="lg" type="submit">
              <Fingerprint aria-hidden="true" size={19} />
              {maskedMobile ? t("resendOtp") : t("requestOtp")}
            </Button>
          </form>

          {maskedMobile ? (
            <form className="warrior-otp-panel" onSubmit={verifyOtp}>
              <div className="warrior-otp-heading">
                <span aria-hidden="true"><Smartphone size={21} /></span>
                <div>
                  <h2>{t("otpTitle")}</h2>
                  <p>{t("otpCopy", {mobile: maskedMobile})}</p>
                </div>
              </div>
              <TextInput
                autoComplete="one-time-code"
                error={verifyError}
                id="warrior-demo-otp"
                inputMode="numeric"
                label={t("otpLabel")}
                maxLength={6}
                onChange={(event) => setOtp(event.target.value.replace(/\D/g, ""))}
                placeholder={t("otpPlaceholder")}
                required
                value={otp}
              />
              <Button className="w-full" isLoading={verifying} size="lg" type="submit">
                {t("verifyAction")}
                <ArrowRight aria-hidden="true" size={18} />
              </Button>
            </form>
          ) : null}

          <Link className="warrior-back-link" href={warriorPath(locale)}>
            <ArrowLeft aria-hidden="true" size={16} /> {t("backToWarriors")}
          </Link>
        </div>

        <div className="warrior-identity-visual">
          <div className="warrior-identity-orbit" aria-hidden="true">
            <span className="warrior-orbit-icon warrior-orbit-person"><UsersRound size={24} /></span>
            <span className="warrior-orbit-icon warrior-orbit-fingerprint"><Fingerprint size={24} /></span>
            <span className="warrior-orbit-icon warrior-orbit-phone"><Smartphone size={24} /></span>
            <div className="warrior-shield-mark"><ShieldCheck size={94} strokeWidth={1.35} /></div>
          </div>
          <h2>{t("secureTitle")}</h2>
          <p>{t("secureCopy")}</p>
          <div className="warrior-privacy-strip">
            <LockKeyhole aria-hidden="true" size={20} />
            <span>{t("privacyCopy")}</span>
          </div>
        </div>
      </section>
    </main>
  );
}

type ProfileSetupForm = {
  city: string;
  preferredLanguage: string;
  state: string;
};

export function WarriorProfileSetup() {
  const t = useTranslations("warriorOnboarding");
  const locale = useLocale();
  const router = useRouter();
  const [identity, setIdentity] = useState<ReturnType<typeof getWarriorIdentity>>(null);
  const [form, setForm] = useState<ProfileSetupForm>({city: "", preferredLanguage: locale, state: ""});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const storedIdentity = getWarriorIdentity();
    const accessToken = getWarriorToken();
    if (!storedIdentity || !accessToken) {
      router.replace(verifyPath(locale));
      return;
    }
    setIdentity(storedIdentity);
    setForm({
      city: storedIdentity.profile.city,
      preferredLanguage: locale,
      state: storedIdentity.profile.state
    });
    setLoading(false);
  }, [locale, router]);

  if (loading || !identity) {
    return <main className="warrior-page shell-container py-10"><StatePanel title={t("profileLoadingTitle")} tone="info">{t("profileLoadingCopy")}</StatePanel></main>;
  }

  const profile = identity.profile;

  async function saveProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getWarriorToken();
    if (!token || !identity) return;
    setSaving(true);
    setError("");
    const payload = {
      display_name: identity.profile.full_name,
      location: [form.city.trim(), form.state.trim()].filter(Boolean).join(", ") || null
    };
    let result = await cyberWarriorsApi.createProfile(payload, {accessToken: token});
    if (!result.ok && (result.error.code === "CONFLICT" || result.error.status === 409)) {
      result = await cyberWarriorsApi.updateMine(payload, {accessToken: token});
    }
    if (!result.ok) {
      setError(t("profileSaveError"));
      setSaving(false);
      return;
    }
    setWarriorProfileSetup({...form, profileId: String(result.data.id ?? "")});
    router.push(applicationPath(locale));
  }

  return (
    <main className="warrior-page shell-container py-7 sm:py-10">
      <section className="warrior-profile-layout">
        <aside className="warrior-profile-rail">
          <p className="warrior-step-label">{t("profileStep")}</p>
          <h1>{t("profileSetupTitle")}</h1>
          <p>{t("profileSetupCopy")}</p>
          <ol>
            <li><CheckCircle2 aria-hidden="true" size={19} /><span>{t("identityVerified")}</span></li>
            <li><CheckCircle2 aria-hidden="true" size={19} /><span>{t("profileCreated")}</span></li>
          </ol>
          <div className="warrior-locked-note"><LockKeyhole aria-hidden="true" size={20} /><span>{t("lockedFieldsCopy")}</span></div>
        </aside>

        <form className="warrior-profile-form" onSubmit={saveProfile}>
          <div className="warrior-profile-heading">
            <div>
              <p className="eyebrow">{t("profileEyebrow")}</p>
              <h2>{t("profileDetailsTitle")}</h2>
              <p>{t("profileDetailsCopy")}</p>
            </div>
            <BadgeCheck aria-hidden="true" size={34} />
          </div>
          <StatePanel title={t("autofillTitle")} tone="success">{t("autofillCopy")}</StatePanel>
          <div className="warrior-profile-grid">
            <TextInput id="warrior-full-name" label={t("fullName")} readOnly value={profile.full_name} />
            <TextInput id="warrior-dob" label={t("dateOfBirth")} readOnly type="date" value={profile.date_of_birth} />
            <TextInput id="warrior-mobile" label={t("registeredMobile")} readOnly value={profile.registered_mobile} />
            <TextInput id="warrior-email" label={t("accountEmail")} readOnly type="email" value={identity.accountEmail} />
            <TextInput id="warrior-state" label={t("state")} onChange={(event) => setForm((current) => ({...current, state: event.target.value}))} required value={form.state} />
            <TextInput id="warrior-city" label={t("city")} onChange={(event) => setForm((current) => ({...current, city: event.target.value}))} required value={form.city} />
            <SelectField
              id="warrior-language"
              label={t("preferredLanguage")}
              onChange={(event) => setForm((current) => ({...current, preferredLanguage: event.target.value}))}
              options={[
                {label: t("languageEnglish"), value: "en"},
                {label: t("languageHindi"), value: "hi"}
              ]}
              value={form.preferredLanguage}
            />
            <TextInput id="warrior-age" label={t("age")} readOnly value={String(profile.age)} />
          </div>
          {error ? <p className="warrior-form-error" role="alert">{error}</p> : null}
          <div className="warrior-profile-actions">
            <Button onClick={() => router.push(verifyPath(locale))} variant="outline">
              <ArrowLeft aria-hidden="true" size={17} /> {t("backAction")}
            </Button>
            <Button isLoading={saving} size="lg" type="submit">
              {t("saveProfile")} <ArrowRight aria-hidden="true" size={18} />
            </Button>
          </div>
        </form>
      </section>
    </main>
  );
}

export function WarriorApplicationStart() {
  const t = useTranslations("warriorOnboarding");
  const locale = useLocale();

  return (
    <main className="warrior-page shell-container py-8 sm:py-12">
      <section className="warrior-application-ready">
        <span className="warrior-ready-icon" aria-hidden="true"><Check size={42} /></span>
        <p className="warrior-step-label">{t("applicationEyebrow")}</p>
        <h1>{t("applicationReadyTitle")}</h1>
        <p>{t("applicationReadyCopy")}</p>
        <div className="warrior-ready-next">
          <FileSearch aria-hidden="true" size={25} />
          <div><strong>{t("resumeNextTitle")}</strong><span>{t("resumeNextCopy")}</span></div>
        </div>
        <Link className="portal-outline-link" href={profilePath(locale)}>
          <ArrowLeft aria-hidden="true" size={17} /> {t("reviewProfileAction")}
        </Link>
      </section>
    </main>
  );
}
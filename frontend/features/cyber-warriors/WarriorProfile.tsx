"use client";

import Link from "next/link";
import {useCallback, useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {ArrowRight, Award, BookOpen, CheckCircle2, Pencil, ShieldCheck, Trophy, Users} from "lucide-react";

import {cyberWarriorsApi, warriorApplicationsApi, warriorReportsApi, type WarriorApplication, type SkillCatalogItem} from "@/lib/api/cyber-warriors";
import {getWarriorIdentity, getWarriorProfileSetup, getWarriorToken} from "@/lib/auth/warrior-session";
import {WarriorShellPage} from "./WarriorAppShell";
import {computeWarriorPoints} from "./warriorReportMeta";

type ProfileApiRecord = {
  bio: string | null;
  certifications: Array<{name: string}>;
  created_at: string;
  display_name: string;
  location: string | null;
  skills: Array<{proficiency_level: string | null; skill_id: string; years_of_experience: number | null}>;
  verification_status: string;
};

type ProfileState = {
  application: WarriorApplication | null;
  profile: ProfileApiRecord | null;
  reports: {status: string}[];
  skillCatalog: SkillCatalogItem[];
};

export function WarriorProfile() {
  const t = useTranslations("warriorProfile");
  const locale = useLocale();
  const router = useRouter();
  const [state, setState] = useState<ProfileState>({application: null, profile: null, reports: [], skillCatalog: []});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const token = getWarriorToken();
    if (!token) {
      router.replace("/" + locale + "/cyber-warrior/verify");
      return;
    }
    const [profileResult, applicationsResult, reportsResult, skillsResult] = await Promise.all([
      cyberWarriorsApi.getMine({accessToken: token}),
      warriorApplicationsApi.listMine({accessToken: token}),
      warriorReportsApi.listMine({accessToken: token}),
      cyberWarriorsApi.listSkills({accessToken: token})
    ]);
    const latestApplication = applicationsResult.ok && applicationsResult.data.length
      ? [...applicationsResult.data].sort((a, b) => b.created_at.localeCompare(a.created_at))[0]
      : null;
    setState({
      application: latestApplication,
      profile: profileResult.ok ? (profileResult.data as unknown as ProfileApiRecord) : null,
      reports: reportsResult.ok ? reportsResult.data.map((item) => ({status: String((item as {status?: unknown}).status ?? "")})) : [],
      skillCatalog: skillsResult.ok ? skillsResult.data : []
    });
    setLoading(false);
  }, [locale, router]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return <main className="warrior-page"><div className="shell-container warrior-application-loading">{t("loadingProfile")}</div></main>;
  }

  const identity = getWarriorIdentity();
  const profileSetup = getWarriorProfileSetup();
  const {application, profile, reports, skillCatalog} = state;
  const dateFormatter = new Intl.DateTimeFormat(locale, {dateStyle: "medium"});
  const notProvided = t("notProvided");

  const skillNames = (profile?.skills ?? [])
    .map((skill) => skillCatalog.find((catalogItem) => catalogItem.id === skill.skill_id)?.name)
    .filter((name): name is string => Boolean(name));
  const maxYearsExperience = (profile?.skills ?? []).reduce((max, skill) => Math.max(max, skill.years_of_experience ?? 0), 0);
  const experienceLevel = maxYearsExperience >= 5 ? t("levelAdvanced") : maxYearsExperience >= 2 ? t("levelIntermediate") : maxYearsExperience > 0 ? t("levelBeginner") : notProvided;
  const certificationNames = (profile?.certifications ?? []).map((cert) => cert.name);

  const filledFields = [profile?.display_name, profile?.bio, profile?.location, skillNames.length > 0, certificationNames.length > 0].filter(Boolean).length;
  const completionPercent = Math.round((filledFields / 5) * 100);

  const submittedCount = reports.filter((r) => r.status !== "DRAFT").length;
  const underReviewCount = reports.filter((r) => r.status === "SUBMITTED" || r.status === "UNDER_REVIEW").length;
  const resolvedCount = reports.filter((r) => r.status === "ACCEPTED").length;

  return (
    <WarriorShellPage
      active="profile"
      identity={{
        label: t("roleLabel"),
        verified: application?.status === "APPROVED" || application?.status === "UNDER_REVIEW" || application?.status === "SUBMITTED",
        warriorId: application?.application_number ?? t("notAvailable")
      }}
    >
      <div className="warrior-dashboard-content">
        <div className="warrior-profile-header-row">
          <div>
            <h1>{t("pageTitle")}</h1>
            <p>{t("pageCopy")}</p>
          </div>
          <Link className="portal-outline-link" href={"/" + locale + "/cyber-warrior/verify/profile"}><Pencil aria-hidden="true" size={16} />{t("editProfile")}</Link>
        </div>

        <section className="warrior-profile-section">
          <h2>{t("personalInfoTitle")}</h2>
          <div className="warrior-profile-avatar-row">
            <span className="warrior-profile-avatar" aria-hidden="true"><ShieldCheck size={40} /></span>
          </div>
          <dl className="warrior-profile-fact-grid">
            <div><dt>{t("username")}</dt><dd>{identity?.accountEmail ?? notProvided}</dd></div>
            <div><dt>{t("warriorId")}</dt><dd>{application?.application_number ?? notProvided}</dd></div>
            <div><dt>{t("dateOfJoining")}</dt><dd>{profile?.created_at ? dateFormatter.format(new Date(profile.created_at)) : notProvided}</dd></div>
            <div><dt>{t("dateOfBirth")}</dt><dd>{identity?.profile.date_of_birth ? dateFormatter.format(new Date(identity.profile.date_of_birth)) : notProvided}</dd></div>
            <div><dt>{t("gender")}</dt><dd>{identity?.profile.gender ?? notProvided}</dd></div>
            <div><dt>{t("preferredLanguage")}</dt><dd>{profileSetup?.preferredLanguage === "hi" ? t("languageHindi") : t("languageEnglish")}</dd></div>
            <div><dt>{t("emailId")}</dt><dd>{identity?.accountEmail ?? notProvided} <CheckCircle2 aria-hidden="true" className="warrior-inline-verified" size={14} /></dd></div>
            <div><dt>{t("mobileNumber")}</dt><dd>{identity?.profile.registered_mobile ?? notProvided} <CheckCircle2 aria-hidden="true" className="warrior-inline-verified" size={14} /></dd></div>
          </dl>
        </section>

        <section className="warrior-profile-section">
          <h2>{t("expertiseTitle")}</h2>
          <dl className="warrior-profile-fact-grid">
            <div><dt>{t("primarySkills")}</dt><dd>{skillNames.length ? skillNames.join(", ") : notProvided}</dd></div>
            <div><dt>{t("experienceLevel")}</dt><dd>{experienceLevel}</dd></div>
            <div><dt>{t("yearsOfExperience")}</dt><dd>{maxYearsExperience > 0 ? t("yearsValue", {years: maxYearsExperience}) : notProvided}</dd></div>
            <div className="wide"><dt>{t("certifications")}</dt><dd>{certificationNames.length ? certificationNames.join(", ") : notProvided}</dd></div>
          </dl>
        </section>

        <section className="warrior-profile-section">
          <h2>{t("bioTitle")}</h2>
          <p className="warrior-profile-bio">{profile?.bio || notProvided}</p>
        </section>
      </div>

      <aside className="warrior-dashboard-rail">
        <div className="warrior-status-widget warrior-completion-widget">
          <h2>{t("completionTitle")}</h2>
          <div className="warrior-completion-ring" style={{background: "conic-gradient(var(--success) " + completionPercent + "%, #e2edf6 0)"}}><span>{completionPercent}%</span></div>
          <p>{completionPercent === 100 ? t("completionFull") : t("completionPartial")}</p>
        </div>
        <div className="warrior-status-widget">
          <h2>{t("badgesTitle")}</h2>
          <div className="warrior-badges-placeholder"><Award aria-hidden="true" size={26} /><p>{t("badgesComingCopy")}</p></div>
          <Link className="warrior-text-link" href={"/" + locale + "/cyber-warrior/badges"}>{t("viewBadges")}<ArrowRight aria-hidden="true" size={15} /></Link>
        </div>
        <div className="warrior-quick-actions">
          <h2>{t("statisticsTitle")}</h2>
          <dl className="warrior-mini-stats">
            <div><dt>{t("statSubmitted")}</dt><dd>{submittedCount}</dd></div>
            <div><dt>{t("statUnderReview")}</dt><dd>{underReviewCount}</dd></div>
            <div><dt>{t("statResolved")}</dt><dd>{resolvedCount}</dd></div>
            <div><dt>{t("statPoints")}</dt><dd>{computeWarriorPoints(reports)}</dd></div>
          </dl>
        </div>
        <div className="warrior-quick-actions">
          <h2>{t("helpfulLinksTitle")}</h2>
          <ul>
            <li><Link href={"/" + locale + "/cyber-warrior/leaderboard"}><span aria-hidden="true"><Trophy size={18} /></span><span><strong>{t("linkLeaderboard")}</strong></span><ArrowRight aria-hidden="true" size={15} /></Link></li>
            <li><Link href={"/" + locale + "/cyber-warrior"}><span aria-hidden="true"><Users size={18} /></span><span><strong>{t("linkGuidelines")}</strong></span><ArrowRight aria-hidden="true" size={15} /></Link></li>
            <li><Link href={"/" + locale + "/cyber-warrior/resources"}><span aria-hidden="true"><BookOpen size={18} /></span><span><strong>{t("linkResources")}</strong></span><ArrowRight aria-hidden="true" size={15} /></Link></li>
          </ul>
        </div>
      </aside>
    </WarriorShellPage>
  );
}

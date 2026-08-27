"use client";

import {useEffect, useState, type FormEvent} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {ArrowLeft, ArrowRight, CheckCircle2, Edit3, GraduationCap, ShieldCheck, Sparkles} from "lucide-react";

import {Button} from "@/components/ui/Button";
import {CheckboxField, SelectField, TextArea, TextInput} from "@/components/ui/FormFields";
import {
  cyberWarriorsApi,
  resumeApi,
  warriorApplicationsApi,
  type ResumeParsingResult,
  type SkillCatalogItem,
  type WarriorApplication
} from "@/lib/api/cyber-warriors";
import {
  getWarriorIdentity,
  getWarriorProfileSetup,
  getWarriorResume,
  getWarriorToken,
  setWarriorApplication
} from "@/lib/auth/warrior-session";
import {ApplicationError, ApplicationHeading, WarriorApplicationFrame} from "./WarriorApplicationShell";

type ReviewForm = {
  bio: string;
  certificationIssuer: string;
  certificationName: string;
  degree: string;
  displayName: string;
  experienceDescription: string;
  experienceOrganization: string;
  experienceTitle: string;
  fieldOfStudy: string;
  institution: string;
  linkedinUrl: string;
  location: string;
  skillId: string;
  statement: string;
};

const emptyForm: ReviewForm = {
  bio: "", certificationIssuer: "", certificationName: "", degree: "", displayName: "",
  experienceDescription: "", experienceOrganization: "", experienceTitle: "", fieldOfStudy: "",
  institution: "", linkedinUrl: "", location: "", skillId: "", statement: ""
};

function value(record: Record<string, unknown> | undefined, key: string) {
  const candidate = record?.[key];
  return typeof candidate === "string" ? candidate : "";
}

function recordAt(items: Array<Record<string, unknown>> | undefined) {
  return items?.[0];
}

export function WarriorApplicationReview() {
  const t = useTranslations("warriorApplication");
  const locale = useLocale();
  const router = useRouter();
  const [mode, setMode] = useState<"edit" | "review">("edit");
  const [form, setForm] = useState<ReviewForm>(emptyForm);
  const [result, setResult] = useState<ResumeParsingResult | null>(null);
  const [skills, setSkills] = useState<SkillCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [declared, setDeclared] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getWarriorToken();
    const resume = getWarriorResume();
    if (!token) {
      router.replace("/" + locale + "/cyber-warrior/verify");
      return;
    }
    if (!resume) {
      router.replace("/" + locale + "/cyber-warrior/apply/resume");
      return;
    }
    let active = true;
    Promise.all([
      resumeApi.getParsingResult(resume.resultId, {accessToken: token}),
      cyberWarriorsApi.listSkills({accessToken: token}),
      cyberWarriorsApi.getMine({accessToken: token})
    ]).then(([parsing, catalog, profile]) => {
      if (!active) return;
      if (!parsing.ok) {
        setError(t("loadReviewError"));
        setLoading(false);
        return;
      }
      const extracted = parsing.data.extracted_data ?? {};
      const profileData = extracted.profile;
      const education = recordAt(extracted.education);
      const experience = recordAt(extracted.experience);
      const certification = recordAt(extracted.certifications);
      const profileRecord = profile.ok ? profile.data : {};
      const setup = getWarriorProfileSetup();
      const identity = getWarriorIdentity();
      const skillNames = extracted.skills ?? [];
      const catalogItems = catalog.ok ? catalog.data : [];
      const suggestedSkill = catalogItems.find((item) => skillNames.some((name) => item.name.toLowerCase() === name.toLowerCase())) ?? catalogItems[0];
      setResult(parsing.data);
      setSkills(catalogItems);
      setForm({
        bio: value(profileData, "bio"),
        certificationIssuer: value(certification, "issuing_organization"),
        certificationName: value(certification, "name"),
        degree: value(education, "degree"),
        displayName: typeof profileRecord.display_name === "string" ? profileRecord.display_name : identity?.profile.full_name ?? "",
        experienceDescription: value(experience, "description"),
        experienceOrganization: value(experience, "organization"),
        experienceTitle: value(experience, "title"),
        fieldOfStudy: value(education, "field_of_study"),
        institution: value(education, "institution"),
        linkedinUrl: typeof profileRecord.linkedin_url === "string" ? profileRecord.linkedin_url : "",
        location: value(profileData, "location") || [setup?.city, setup?.state].filter(Boolean).join(", "),
        skillId: suggestedSkill?.id ?? "",
        statement: ""
      });
      setLoading(false);
    });
    return () => { active = false; };
  }, [locale, router, t]);

  function update<K extends keyof ReviewForm>(key: K, next: ReviewForm[K]) {
    setForm((current) => ({...current, [key]: next}));
  }

  function validateDetails(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!form.displayName.trim() || !form.institution.trim() || !form.degree.trim() || !form.experienceOrganization.trim() || !form.experienceTitle.trim()) {
      setError(t("requiredDetailsError"));
      return;
    }
    setMode("review");
    window.scrollTo({top: 0, behavior: "smooth"});
  }

  async function submitApplication() {
    const token = getWarriorToken();
    const resume = getWarriorResume();
    if (!token || !resume || !result || !declared) return;
    setSubmitting(true);
    setError("");

    if (!result.confirmed_at) {
      const confirmed = await resumeApi.confirmParsing(resume.resultId, {
        bio: form.bio || null,
        certifications: form.certificationName ? [{
          issuing_organization: form.certificationIssuer || null,
          name: form.certificationName
        }] : [],
        display_name: form.displayName,
        education: [{
          degree: form.degree,
          field_of_study: form.fieldOfStudy || null,
          institution: form.institution
        }],
        experience: [{
          description: form.experienceDescription || null,
          is_current: true,
          organization: form.experienceOrganization,
          title: form.experienceTitle
        }],
        github_url: null,
        linkedin_url: form.linkedinUrl || null,
        location: form.location || null,
        skills: form.skillId ? [{proficiency_level: "INTERMEDIATE", skill_id: form.skillId}] : []
      }, {accessToken: token});
      if (!confirmed.ok) {
        setError(t("confirmError"));
        setSubmitting(false);
        return;
      }
    }

    let application: WarriorApplication | null = null;
    const created = await warriorApplicationsApi.create({statement: form.statement || t("defaultStatement")}, {accessToken: token});
    if (created.ok) {
      const submitted = await warriorApplicationsApi.submit(created.data.id, {accessToken: token});
      if (submitted.ok) application = submitted.data;
    } else if (created.error.status === 409) {
      const existing = await warriorApplicationsApi.listMine({accessToken: token});
      if (existing.ok) {
        const candidate = existing.data.find((item) => ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "APPROVED"].includes(item.status));
        if (candidate?.status === "DRAFT") {
          const submitted = await warriorApplicationsApi.submit(candidate.id, {accessToken: token});
          if (submitted.ok) application = submitted.data;
        } else {
          application = candidate ?? null;
        }
      }
    }

    if (!application) {
      setError(t("submitError"));
      setSubmitting(false);
      return;
    }
    setWarriorApplication(application);
    router.push("/" + locale + "/cyber-warrior/apply/submitted");
  }

  if (loading) {
    return <WarriorApplicationFrame activeStep={2}><div className="warrior-application-loading">{t("loadingReview")}</div></WarriorApplicationFrame>;
  }

  const identity = getWarriorIdentity();
  const selectedSkill = skills.find((item) => item.id === form.skillId);

  if (mode === "review") {
    return (
      <WarriorApplicationFrame activeStep={3}>
        <ApplicationHeading eyebrow={t("reviewEyebrow")} title={t("reviewTitle")} copy={t("reviewCopy")} />
        <div className="warrior-review-toolbar">
          <span><CheckCircle2 aria-hidden="true" size={18} />{t("userReviewed")}</span>
          <Button onClick={() => setMode("edit")} size="sm" variant="outline"><Edit3 size={16} />{t("editAction")}</Button>
        </div>
        <div className="warrior-review-sections">
          <section><h3>{t("personalTitle")}</h3><dl><div><dt>{t("fullName")}</dt><dd>{form.displayName}</dd></div><div><dt>{t("email")}</dt><dd>{identity?.accountEmail}</dd></div><div><dt>{t("location")}</dt><dd>{form.location || t("notProvided")}</dd></div><div><dt>{t("primarySkill")}</dt><dd>{selectedSkill?.name ?? t("notProvided")}</dd></div></dl></section>
          <section><h3>{t("educationTitle")}</h3><dl><div><dt>{t("institution")}</dt><dd>{form.institution}</dd></div><div><dt>{t("degree")}</dt><dd>{form.degree}</dd></div><div><dt>{t("fieldOfStudy")}</dt><dd>{form.fieldOfStudy || t("notProvided")}</dd></div></dl></section>
          <section><h3>{t("experienceTitle")}</h3><dl><div><dt>{t("organization")}</dt><dd>{form.experienceOrganization}</dd></div><div><dt>{t("role")}</dt><dd>{form.experienceTitle}</dd></div><div className="wide"><dt>{t("experienceDetails")}</dt><dd>{form.experienceDescription || t("notProvided")}</dd></div></dl></section>
          <section><h3>{t("certificationTitle")}</h3><dl><div><dt>{t("certificationName")}</dt><dd>{form.certificationName || t("notProvided")}</dd></div><div><dt>{t("issuer")}</dt><dd>{form.certificationIssuer || t("notProvided")}</dd></div></dl></section>
        </div>
        <TextArea id="warrior-statement" label={t("statement")} maxLength={5000} onChange={(event) => update("statement", event.target.value)} value={form.statement} />
        <div className="warrior-declaration">
          <CheckboxField checked={declared} id="warrior-declaration" label={t("declaration")} onCheckedChange={(event) => setDeclared(event.target.checked)} required />
        </div>
        <ApplicationError message={error} />
        <footer className="warrior-application-actions">
          <Button onClick={() => setMode("edit")} variant="outline"><ArrowLeft size={17} />{t("backDetails")}</Button>
          <Button disabled={!declared} isLoading={submitting} onClick={submitApplication}>{t("submitAction")}<ArrowRight size={17} /></Button>
        </footer>
      </WarriorApplicationFrame>
    );
  }

  return (
    <WarriorApplicationFrame activeStep={2}>
      <ApplicationHeading eyebrow={t("detailsEyebrow")} title={t("detailsTitle")} copy={t("detailsCopy")} />
      <div className="warrior-ai-review-note"><Sparkles aria-hidden="true" size={21} /><div><strong>{t("untrustedTitle")}</strong><p>{t("untrustedCopy")}</p></div></div>
      <form onSubmit={validateDetails}>
        <div className="warrior-application-form-grid">
          <TextInput id="warrior-display-name" label={t("displayName")} onChange={(event) => update("displayName", event.target.value)} required value={form.displayName} />
          <TextInput id="warrior-location" label={t("location")} onChange={(event) => update("location", event.target.value)} value={form.location} />
          <TextInput id="warrior-linkedin" label={t("linkedin")} onChange={(event) => update("linkedinUrl", event.target.value)} type="url" value={form.linkedinUrl} />
          <SelectField id="warrior-skill" label={t("primarySkill")} onChange={(event) => update("skillId", event.target.value)} options={[{label: t("selectSkill"), value: ""}, ...skills.map((item) => ({label: item.name, value: item.id}))]} value={form.skillId} />
        </div>
        <TextArea id="warrior-bio" label={t("bio")} maxLength={5000} onChange={(event) => update("bio", event.target.value)} value={form.bio} />
        <fieldset className="warrior-application-fieldset"><legend><GraduationCap size={18} />{t("educationTitle")}</legend><div className="warrior-application-form-grid"><TextInput id="warrior-institution" label={t("institution")} onChange={(event) => update("institution", event.target.value)} required value={form.institution} /><TextInput id="warrior-degree" label={t("degree")} onChange={(event) => update("degree", event.target.value)} required value={form.degree} /><TextInput id="warrior-field" label={t("fieldOfStudy")} onChange={(event) => update("fieldOfStudy", event.target.value)} value={form.fieldOfStudy} /></div></fieldset>
        <fieldset className="warrior-application-fieldset"><legend>{t("experienceTitle")}</legend><div className="warrior-application-form-grid"><TextInput id="warrior-organization" label={t("organization")} onChange={(event) => update("experienceOrganization", event.target.value)} required value={form.experienceOrganization} /><TextInput id="warrior-role" label={t("role")} onChange={(event) => update("experienceTitle", event.target.value)} required value={form.experienceTitle} /></div><TextArea id="warrior-experience" label={t("experienceDetails")} onChange={(event) => update("experienceDescription", event.target.value)} value={form.experienceDescription} /></fieldset>
        <fieldset className="warrior-application-fieldset"><legend>{t("certificationTitle")}</legend><div className="warrior-application-form-grid"><TextInput id="warrior-certificate" label={t("certificationName")} onChange={(event) => update("certificationName", event.target.value)} value={form.certificationName} /><TextInput id="warrior-issuer" label={t("issuer")} onChange={(event) => update("certificationIssuer", event.target.value)} value={form.certificationIssuer} /></div></fieldset>
        <ApplicationError message={error} />
        <footer className="warrior-application-actions">
          <Button onClick={() => router.push("/" + locale + "/cyber-warrior/apply/resume")} type="button" variant="outline"><ArrowLeft size={17} />{t("backUpload")}</Button>
          <Button type="submit">{t("reviewAction")}<ArrowRight size={17} /></Button>
        </footer>
      </form>
    </WarriorApplicationFrame>
  );
}

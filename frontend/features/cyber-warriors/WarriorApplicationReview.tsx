"use client";

import {useEffect, useState, type FormEvent} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {ArrowLeft, ArrowRight, CheckCircle2, Edit3, GraduationCap, Plus, ShieldCheck, Sparkles, Trash2} from "lucide-react";

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

type SkillRow = {proficiencyLevel: string; skillId: string; yearsOfExperience: string};

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
  skills: SkillRow[];
  statement: string;
};

const emptyForm: ReviewForm = {
  bio: "", certificationIssuer: "", certificationName: "", degree: "", displayName: "",
  experienceDescription: "", experienceOrganization: "", experienceTitle: "", fieldOfStudy: "",
  institution: "", linkedinUrl: "", location: "", skills: [], statement: ""
};

const emptySkillRow: SkillRow = {proficiencyLevel: "INTERMEDIATE", skillId: "", yearsOfExperience: ""};

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
      const suggestedSkills = catalogItems.filter((item) => skillNames.some((name) => item.name.toLowerCase() === name.toLowerCase()));
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
        skills: suggestedSkills.map((item) => ({...emptySkillRow, skillId: item.id})),
        statement: ""
      });
      setLoading(false);
    });
    return () => { active = false; };
  }, [locale, router, t]);

  function update<K extends keyof ReviewForm>(key: K, next: ReviewForm[K]) {
    setForm((current) => ({...current, [key]: next}));
  }

  function addSkillRow() {
    setForm((current) => ({...current, skills: [...current.skills, {...emptySkillRow}]}));
  }

  function updateSkillRow(index: number, patch: Partial<SkillRow>) {
    setForm((current) => ({...current, skills: current.skills.map((row, rowIndex) => (rowIndex === index ? {...row, ...patch} : row))}));
  }

  function removeSkillRow(index: number) {
    setForm((current) => ({...current, skills: current.skills.filter((_, rowIndex) => rowIndex !== index)}));
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
        skills: form.skills
          .filter((row) => row.skillId)
          .map((row) => ({
            proficiency_level: row.proficiencyLevel || null,
            skill_id: row.skillId,
            years_of_experience: row.yearsOfExperience ? Number(row.yearsOfExperience) : null
          }))
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
  const chosenSkillIds = new Set(form.skills.map((row) => row.skillId));
  const selectedSkillNames = form.skills
    .map((row) => skills.find((item) => item.id === row.skillId)?.name)
    .filter((name): name is string => Boolean(name));
  const proficiencyOptions = [
    {label: t("proficiencyBeginner"), value: "BEGINNER"},
    {label: t("proficiencyIntermediate"), value: "INTERMEDIATE"},
    {label: t("proficiencyAdvanced"), value: "ADVANCED"}
  ];

  if (mode === "review") {
    return (
      <WarriorApplicationFrame activeStep={3}>
        <ApplicationHeading eyebrow={t("reviewEyebrow")} title={t("reviewTitle")} copy={t("reviewCopy")} />
        <div className="warrior-review-toolbar">
          <span><CheckCircle2 aria-hidden="true" size={18} />{t("userReviewed")}</span>
          <Button onClick={() => setMode("edit")} size="sm" variant="outline"><Edit3 size={16} />{t("editAction")}</Button>
        </div>
        <div className="warrior-review-sections">
          <section><h3>{t("personalTitle")}</h3><dl><div><dt>{t("fullName")}</dt><dd>{form.displayName}</dd></div><div><dt>{t("email")}</dt><dd>{identity?.accountEmail}</dd></div><div><dt>{t("location")}</dt><dd>{form.location || t("notProvided")}</dd></div><div className="wide"><dt>{t("skillsLabel")}</dt><dd>{selectedSkillNames.length ? selectedSkillNames.join(", ") : t("notProvided")}</dd></div></dl></section>
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
        </div>
        <TextArea id="warrior-bio" label={t("bio")} maxLength={5000} onChange={(event) => update("bio", event.target.value)} value={form.bio} />
        <fieldset className="warrior-application-fieldset">
          <legend>{t("skillsLabel")}</legend>
          {form.skills.length === 0 ? <p className="warrior-skills-empty">{t("noSkillsAdded")}</p> : null}
          <div className="warrior-skill-rows">
            {form.skills.map((row, index) => (
              <div className="warrior-skill-row" key={index}>
                <SelectField
                  id={"warrior-skill-" + index}
                  label={t("skillLabel")}
                  onChange={(event) => updateSkillRow(index, {skillId: event.target.value})}
                  options={[
                    {label: t("selectSkill"), value: ""},
                    ...skills
                      .filter((item) => item.id === row.skillId || !chosenSkillIds.has(item.id))
                      .map((item) => ({label: item.name, value: item.id}))
                  ]}
                  value={row.skillId}
                />
                <SelectField
                  id={"warrior-skill-level-" + index}
                  label={t("proficiencyLabel")}
                  onChange={(event) => updateSkillRow(index, {proficiencyLevel: event.target.value})}
                  options={proficiencyOptions}
                  value={row.proficiencyLevel}
                />
                <TextInput
                  id={"warrior-skill-years-" + index}
                  inputMode="numeric"
                  label={t("yearsOfExperienceLabel")}
                  max={80}
                  min={0}
                  onChange={(event) => updateSkillRow(index, {yearsOfExperience: event.target.value.replace(/\D/g, "")})}
                  type="number"
                  value={row.yearsOfExperience}
                />
                <button aria-label={t("removeSkillAction")} className="warrior-remove-skill" onClick={() => removeSkillRow(index)} type="button"><Trash2 aria-hidden="true" size={16} /></button>
              </div>
            ))}
          </div>
          <Button onClick={addSkillRow} size="sm" type="button" variant="outline"><Plus aria-hidden="true" size={16} />{t("addSkillAction")}</Button>
        </fieldset>
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

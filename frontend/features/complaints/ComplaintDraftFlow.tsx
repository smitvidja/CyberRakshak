"use client";

import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {Baby, UserRound, UsersRound} from "lucide-react";

import {Button} from "@/components/ui/Button";
import {StepIndicator} from "@/components/common/Workflow";
import {UploadDropzone} from "@/components/evidence/UploadDropzone";
import {TextArea, TextInput} from "@/components/ui/FormFields";
import {StatePanel, SurfaceCard} from "@/components/ui/Surface";
import {complaintCategoriesApi, complaintsApi, evidenceApi} from "@/lib/api/complaints";
import type {ApiRecord} from "@/lib/api/auth";
import {addComplaintEvidence, getAccessToken, getComplaintDraft, getComplaintEvidence, getReportCategoryHint, getReportMode, setComplaintDraft} from "@/lib/auth/citizen-session";

type Category = {description: string | null; id: string; name: string};
type FieldErrors = Record<string, string>;
type IncidentForm = {
  categoryId: string;
  city: string;
  description: string;
  district: string;
  incidentAt: string;
  lossAmount: string;
  state: string;
  title: string;
};
type PersonForm = {alias: string; contactDetails: string; description: string; name: string};
type EvidenceItem = {fileName: string; fileSize: number; id: string};

const emptyIncidentForm: IncidentForm = {
  categoryId: "",
  city: "",
  description: "",
  district: "",
  incidentAt: "",
  lossAmount: "",
  state: "",
  title: ""
};

const emptyPersonForm: PersonForm = {alias: "", contactDetails: "", description: "", name: ""};

function asString(value: unknown) {
  return typeof value === "string" ? value : "";
}

function toLocalDateTimeInput(value: string | Date = new Date()) {
  const date = typeof value === "string" ? new Date(value) : value;
  const localTime = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return localTime.toISOString().slice(0, 16);
}

function categoryMatchesHint(name: string, hint: string) {
  const normalized = name.toLowerCase();
  const keywords: Record<string, string[]> = {
    women: ["women", "child"], financial: ["financial", "fraud"], identity: ["identity"], harassment: ["harassment", "bullying"], commerce: ["commerce", "shopping", "marketplace"], other: ["other"]
  };
  const key = hint === "women-child" ? "women" : hint;
  return (keywords[key] ?? [key]).some((keyword) => normalized.includes(keyword));
}

function asRecord(value: unknown): ApiRecord | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as ApiRecord : null;
}

function incidentFromDraft(draft: ApiRecord): IncidentForm {
  const location = asRecord(draft.location) ?? {};
  return {
    categoryId: asString(draft.category_id) || asString(asRecord(draft.category)?.id),
    city: asString(location.city),
    description: asString(draft.description),
    district: asString(location.district),
    incidentAt: asString(draft.incident_at) ? toLocalDateTimeInput(asString(draft.incident_at)) : "",
    lossAmount: draft.financial_loss_amount === null || draft.financial_loss_amount === undefined ? "" : String(draft.financial_loss_amount),
    state: asString(location.state),
    title: asString(draft.title)
  };
}

function peopleFromDraft(draft: ApiRecord): PersonForm[] {
  const suspects = draft.suspects;
  if (!Array.isArray(suspects) || suspects.length === 0) {
    return [emptyPersonForm];
  }

  return suspects.map((suspect) => {
    const record = asRecord(suspect) ?? {};
    return {
      alias: asString(record.alias),
      contactDetails: asString(record.contact_details),
      description: asString(record.description),
      name: asString(record.name)
    };
  });
}

function isIdentifiedReport() {
  return getReportMode() === "identified";
}

function requestOptions() {
  return isIdentifiedReport() ? {accessToken: getAccessToken() ?? undefined} : undefined;
}

function incidentPath(locale: string, draftId: string) {
  return "/" + locale + "/report-crime/" + draftId + "/incident";
}

function peoplePath(locale: string, draftId: string) {
  return "/" + locale + "/report-crime/" + draftId + "/people";
}

function reviewPath(locale: string, draftId: string) {
  return "/" + locale + "/report-crime/" + draftId + "/review";
}

function workflowSteps(t: ReturnType<typeof useTranslations>, current: "incident" | "people") {
  return [
    {label: t("steps.incident"), status: current === "incident" ? "current" : "completed"} as const,
    {label: t("steps.people"), status: current === "people" ? "current" : "upcoming"} as const,
    {label: t("steps.review"), status: "upcoming"} as const
  ];
}

export function ComplaintIncidentStep({draftId}: {draftId: string}) {
  const t = useTranslations("complaintDraft");
  const locale = useLocale();
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState<IncidentForm>(emptyIncidentForm);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [serviceError, setServiceError] = useState("");
  const [evidenceDescription, setEvidenceDescription] = useState("");
  const [evidenceError, setEvidenceError] = useState("");
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [evidenceItems, setEvidenceItems] = useState<EvidenceItem[]>([]);

  useEffect(() => {
    let active = true;

    async function load() {
      const categoryResult = await complaintCategoriesApi.list();
      if (!active) {
        return;
      }
      if (categoryResult.ok) {
        const loadedCategories = categoryResult.data.map((item) => ({
          description: typeof item.description === "string" ? item.description : null,
          id: asString(item.id),
          name: asString(item.name)
        }));
        setCategories(loadedCategories);
        const categoryHint = getReportCategoryHint();
        const hintedCategory = categoryHint ? loadedCategories.find((category) => categoryMatchesHint(category.name, categoryHint)) : undefined;
        if (hintedCategory) setForm((current) => current.categoryId ? current : {...current, categoryId: hintedCategory.id});
      } else {
        setServiceError(t("categoriesError"));
      }

      if (draftId !== "new") {
        const cachedDraft = getComplaintDraft();
        if (cachedDraft?.id === draftId) {
          setForm(incidentFromDraft(cachedDraft.data));
          setEvidenceItems(getComplaintEvidence(draftId));
        }

        if (isIdentifiedReport() && getAccessToken()) {
          const draftResult = await complaintsApi.getById(draftId, requestOptions());
          if (active && draftResult.ok) {
            setForm(incidentFromDraft(draftResult.data));
            setComplaintDraft({data: draftResult.data, id: draftId});
          } else if (active && !cachedDraft) {
            setServiceError(t("draftUnavailable"));
          }
        } else if (!cachedDraft) {
          setServiceError(t("draftUnavailable"));
        }
      }
      if (active) {
        setLoading(false);
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [draftId, t]);

  function updateField(field: keyof IncidentForm, value: string) {
    setForm((current) => ({...current, [field]: value}));
    setErrors((current) => ({...current, [field]: ""}));
  }

  function validate() {
    const nextErrors: FieldErrors = {};
    if (!form.categoryId) {
      nextErrors.categoryId = t("validation.category");
    }
    if (form.title.trim().length < 3) {
      nextErrors.title = t("validation.title");
    }
    if (form.description.trim().length < 10) {
      nextErrors.description = t("validation.description");
    }
    if (form.lossAmount && (!/^\d+(\.\d{1,2})?$/.test(form.lossAmount) || Number(form.lossAmount) < 0)) {
      nextErrors.lossAmount = t("validation.amount");
    }
    if (form.incidentAt && new Date(form.incidentAt).getTime() > Date.now()) {
      nextErrors.incidentAt = t("validation.futureIncident");
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function saveDraft(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const shouldContinue = submitter?.value === "continue";
    if (!validate()) {
      return;
    }

    setSaving(true);
    setMessage("");
    setServiceError("");
    const location = {city: form.city || null, district: form.district || null, state: form.state || null};
    const hasLocation = Boolean(form.city || form.district || form.state);
    const payload: ApiRecord = {
      category_id: form.categoryId,
      description: form.description.trim(),
      financial_loss_amount: form.lossAmount || null,
      incident_at: form.incidentAt ? new Date(form.incidentAt).toISOString() : null,
      location: hasLocation ? location : null,
      title: form.title.trim()
    };
    const result = draftId === "new"
      ? await complaintsApi.createDraft({...payload, is_anonymous: !isIdentifiedReport()}, requestOptions())
      : await complaintsApi.updateDraft(draftId, payload, requestOptions());

    if (!result.ok) {
      setServiceError(t("saveError"));
      setSaving(false);
      return;
    }

    const savedDraftId = asString(result.data.id);
    if (evidenceFile) {
      const evidencePayload = new FormData();
      evidencePayload.set("complaint_id", savedDraftId);
      evidencePayload.set("description", evidenceDescription.trim());
      evidencePayload.set("file", evidenceFile);
      const uploadResult = await evidenceApi.upload(evidencePayload, requestOptions());
      if (!uploadResult.ok) {
        setEvidenceError(t("evidenceError"));
      } else {
        const item = {
          fileName: asString(uploadResult.data.file_name) || evidenceFile.name,
          fileSize: Number(uploadResult.data.file_size) || evidenceFile.size,
          id: asString(uploadResult.data.id)
        };
        addComplaintEvidence(savedDraftId, item);
        setEvidenceItems((current) => [...current, item]);
        setEvidenceFile(null);
        setEvidenceDescription("");
        setEvidenceError("");
      }
    }
    setComplaintDraft({data: result.data, id: savedDraftId});
    setForm(incidentFromDraft(result.data));
    setMessage(t("saved"));
    setSaving(false);
    if (shouldContinue) {
      router.push(peoplePath(locale, savedDraftId));
    }
    if (draftId === "new") {
      router.replace(incidentPath(locale, savedDraftId));
    }
  }

  if (loading) {
    return <main className="citizen-page shell-container py-8 sm:py-12"><StatePanel title={t("loadingTitle")} tone="loading">{t("loadingCopy")}</StatePanel></main>;
  }

  const savedDraftId = draftId === "new" ? null : draftId;
  return (
    <main className="citizen-page citizen-incident-page shell-container py-8 sm:py-12">
      <div className="citizen-workspace mx-auto max-w-5xl space-y-6">
        <p className="eyebrow">{t("incidentEyebrow")}</p>
        <h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("incidentTitle")}</h1>
        <p className="max-w-3xl text-base leading-7 text-[var(--muted)]">{t("incidentIntro")}</p>
        <StepIndicator label={t("steps.label")} steps={workflowSteps(t, "incident")} />
        {serviceError ? <StatePanel title={t("errorTitle")} tone="error">{serviceError}</StatePanel> : null}
        {message ? <StatePanel title={t("savedTitle")} tone="success">{message}</StatePanel> : null}
        <form className="space-y-6" onSubmit={saveDraft} noValidate>
          <SurfaceCard className="citizen-category-panel" heading={t("categoryTitle")}>
            <fieldset>
              <legend className="text-sm font-bold text-[var(--ink)]">{t("categoryLabel")}</legend>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {categories.map((category) => <button aria-pressed={form.categoryId === category.id} className={["min-h-24 rounded-[var(--radius)] border p-4 text-left transition-colors", form.categoryId === category.id ? "border-[var(--blue)] bg-[var(--blue-soft)]" : "border-[var(--border)] bg-white hover:bg-[#f5f8fb]"].join(" ")} key={category.id} onClick={() => updateField("categoryId", category.id)} type="button"><strong className="block text-sm text-[var(--navy)]">{category.name}</strong>{category.description ? <span className="mt-2 block text-xs leading-5 text-[var(--muted)]">{category.description}</span> : null}</button>)}
              </div>
              {errors.categoryId ? <p className="mt-2 text-sm font-medium text-[var(--danger)]" role="alert">{errors.categoryId}</p> : null}
            </fieldset>
          </SurfaceCard>
          <SurfaceCard className="citizen-detail-panel" heading={t("detailsTitle")}>
            <div className="grid gap-4 sm:grid-cols-2">
              <TextInput error={errors.title} id="incident-title" label={t("titleLabel")} onChange={(event) => updateField("title", event.target.value)} required value={form.title} />
              <TextInput error={errors.incidentAt} id="incident-date" label={t("incidentAtLabel")} max={toLocalDateTimeInput()} onChange={(event) => updateField("incidentAt", event.target.value)} type="datetime-local" value={form.incidentAt} />
              <TextInput error={errors.lossAmount} id="loss-amount" label={t("lossAmountLabel")} min="0" onChange={(event) => updateField("lossAmount", event.target.value)} step="0.01" type="number" value={form.lossAmount} />
              <div className="hidden sm:block" aria-hidden="true" />
            </div>
            <div className="mt-4"><TextArea description={t("descriptionHelp")} error={errors.description} id="incident-description" label={t("descriptionLabel")} onChange={(event) => updateField("description", event.target.value)} required value={form.description} /></div>
          </SurfaceCard>
          <SurfaceCard className="citizen-location-panel" heading={t("locationTitle")}>
            <div className="grid gap-4 sm:grid-cols-3">
              <TextInput id="incident-city" label={t("cityLabel")} onChange={(event) => updateField("city", event.target.value)} value={form.city} />
              <TextInput id="incident-district" label={t("districtLabel")} onChange={(event) => updateField("district", event.target.value)} value={form.district} />
              <TextInput id="incident-state" label={t("stateLabel")} onChange={(event) => updateField("state", event.target.value)} value={form.state} />
            </div>
          </SurfaceCard>
          <SurfaceCard className="citizen-evidence-panel" heading={t("evidenceTitle")}>
            <UploadDropzone accept=".pdf,.png,.jpg,.jpeg" browseLabel={t("browseEvidence")} description={t("evidenceDescription")} error={evidenceError} id="complaint-evidence" maxSizeLabel={t("evidenceSize")} onFilesSelected={(files) => { setEvidenceFile(files[0] ?? null); setEvidenceError(""); }} title={evidenceFile ? evidenceFile.name : t("evidenceUploadTitle")} />
            <div className="mt-4 max-w-xl"><TextInput id="evidence-description" label={t("evidenceDescriptionLabel")} onChange={(event) => setEvidenceDescription(event.target.value)} value={evidenceDescription} /></div>
            <p className="mt-3 text-xs leading-5 text-[var(--muted)]">{t("evidenceSaveCopy")}</p>
            {evidenceItems.length > 0 ? <ul className="mt-4 divide-y divide-[var(--border)] rounded-[var(--radius)] border border-[var(--border)]">{evidenceItems.map((item) => <li className="px-4 py-3 text-sm text-[var(--ink)]" key={item.id}>{t("evidenceUploaded", {fileName: item.fileName, fileSize: item.fileSize})}</li>)}</ul> : null}
          </SurfaceCard>
          <div className="flex flex-wrap gap-3"><Button isLoading={saving} name="intent" type="submit" value="save">{savedDraftId ? t("saveChanges") : t("saveDraft")}</Button><Button disabled={saving} name="intent" type="submit" value="continue" variant="outline">{t("continuePeople")}</Button></div>
        </form>
      </div>
    </main>
  );
}

export function ComplaintPeopleStep({draftId}: {draftId: string}) {
  const t = useTranslations("complaintDraft");
  const locale = useLocale();
  const router = useRouter();
  const [reportingFor, setReportingFor] = useState<"SELF" | "CHILD" | "OTHER">("SELF");
  const [affectedPersonName, setAffectedPersonName] = useState("");
  const [hasSuspectInfo, setHasSuspectInfo] = useState(false);
  const [people, setPeople] = useState<PersonForm[]>([emptyPersonForm]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  function applyDraft(data: ApiRecord) {
    const nextPeople = peopleFromDraft(data);
    const mode = asString(data.reporting_for);
    setReportingFor(mode === "CHILD" || mode === "OTHER" ? mode : "SELF");
    setAffectedPersonName(asString(data.affected_person_name));
    setPeople(nextPeople);
    setHasSuspectInfo(nextPeople.some((person) => Object.values(person).some(Boolean)));
  }

  useEffect(() => {
    let active = true;
    async function load() {
      const cachedDraft = getComplaintDraft();
      if (cachedDraft?.id === draftId) applyDraft(cachedDraft.data);
      if (isIdentifiedReport() && getAccessToken()) {
        const result = await complaintsApi.getById(draftId, requestOptions());
        if (!active) return;
        if (result.ok) {
          applyDraft(result.data);
          setComplaintDraft({data: result.data, id: draftId});
        } else if (!cachedDraft) {
          setError(t("draftUnavailable"));
        }
      } else if (!cachedDraft) {
        setError(t("draftUnavailable"));
      }
      if (active) setLoading(false);
    }
    void load();
    return () => { active = false; };
  }, [draftId, t]);

  function updatePerson(index: number, field: keyof PersonForm, value: string) {
    setPeople((current) => current.map((person, personIndex) => personIndex === index ? {...person, [field]: value} : person));
  }

  async function savePeople(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (reportingFor !== "SELF" && affectedPersonName.trim().length < 2) {
      setError(t("affectedNameRequired"));
      return;
    }
    setSaving(true);
    setError("");
    const suspects = hasSuspectInfo ? people.filter((person) => Object.values(person).some(Boolean)).map((person) => ({alias: person.alias || null, contact_details: person.contactDetails || null, description: person.description || null, name: person.name || null})) : [];
    const result = await complaintsApi.updateDraft(draftId, {
      reporting_for: reportingFor,
      affected_person_name: reportingFor === "SELF" ? null : affectedPersonName.trim(),
      suspects
    }, requestOptions());
    if (!result.ok) {
      setError(t("saveError"));
      setSaving(false);
      return;
    }
    setComplaintDraft({data: result.data, id: draftId});
    setSaving(false);
    router.push(reviewPath(locale, draftId));
  }

  if (loading) return <main className="citizen-page shell-container py-8 sm:py-12"><StatePanel title={t("loadingTitle")} tone="loading">{t("loadingCopy")}</StatePanel></main>;

  const affectedOptions = [
    {value: "SELF" as const, icon: UserRound, title: t("affectedSelfTitle"), copy: t("affectedSelfCopy")},
    {value: "CHILD" as const, icon: Baby, title: t("affectedChildTitle"), copy: t("affectedChildCopy")},
    {value: "OTHER" as const, icon: UsersRound, title: t("affectedOtherTitle"), copy: t("affectedOtherCopy")}
  ];

  return (
    <main className="citizen-page citizen-people-page shell-container py-8 sm:py-12">
      <div className="citizen-workspace mx-auto max-w-5xl space-y-6">
        <p className="eyebrow">{t("peopleEyebrow")}</p><h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("peopleTitle")}</h1><p className="max-w-3xl text-base leading-7 text-[var(--muted)]">{t("peopleIntro")}</p>
        <StepIndicator label={t("steps.label")} steps={workflowSteps(t, "people")} />
        {error ? <StatePanel title={t("errorTitle")} tone="error">{error}</StatePanel> : null}
        <form className="space-y-6" onSubmit={savePeople}>
          <SurfaceCard heading={t("affectedTitle")}>
            <fieldset><legend className="text-sm font-semibold text-[var(--muted)]">{t("affectedLegend")}</legend><div className="mt-4 grid gap-3 md:grid-cols-3">{affectedOptions.map(({value, icon: Icon, title, copy}) => <button aria-pressed={reportingFor === value} className={["affected-person-option flex min-h-[118px] items-start gap-4 rounded-[7px] border p-4 text-left", reportingFor === value ? "border-[var(--blue)] bg-[var(--blue-soft)]" : "border-[var(--border)] bg-white"].join(" ")} key={value} onClick={() => { setReportingFor(value); setError(""); }} type="button"><span aria-hidden="true" className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-white text-[var(--blue)]"><Icon size={23} strokeWidth={1.7} /></span><span><strong className="block text-sm text-[var(--navy)]">{title}</strong><span className="mt-1 block text-xs leading-5 text-[var(--muted)]">{copy}</span></span></button>)}</div></fieldset>
            {reportingFor !== "SELF" ? <div className="mt-5 max-w-xl"><TextInput id="affected-person-name" label={t("affectedNameLabel")} onChange={(event) => { setAffectedPersonName(event.target.value); setError(""); }} required value={affectedPersonName} /></div> : null}
          </SurfaceCard>
          <SurfaceCard heading={t("suspectQuestionTitle")}>
            <p className="text-sm leading-6 text-[var(--muted)]">{t("suspectQuestionCopy")}</p>
            <div className="mt-4 flex flex-wrap gap-3"><Button onClick={() => setHasSuspectInfo(true)} variant={hasSuspectInfo ? "primary" : "outline"}>{t("suspectYes")}</Button><Button onClick={() => setHasSuspectInfo(false)} variant={!hasSuspectInfo ? "primary" : "outline"}>{t("suspectNo")}</Button></div>
            {hasSuspectInfo ? <div className="mt-6 space-y-6">{people.map((person, index) => <fieldset className="border-t border-[var(--border)] pt-5" key={index}><legend className="text-sm font-bold text-[var(--navy)]">{t("personNumber", {number: index + 1})}</legend><div className="mt-3 grid gap-4 sm:grid-cols-2"><TextInput id={"person-name-" + index} label={t("personName")} onChange={(event) => updatePerson(index, "name", event.target.value)} value={person.name} /><TextInput id={"person-alias-" + index} label={t("personAlias")} onChange={(event) => updatePerson(index, "alias", event.target.value)} value={person.alias} /><TextInput id={"person-contact-" + index} label={t("personContact")} onChange={(event) => updatePerson(index, "contactDetails", event.target.value)} value={person.contactDetails} /><TextArea id={"person-description-" + index} label={t("personDescription")} onChange={(event) => updatePerson(index, "description", event.target.value)} value={person.description} /></div></fieldset>)}</div> : <StatePanel title={t("noSuspectTitle")} tone="info">{t("noSuspectCopy")}</StatePanel>}
          </SurfaceCard>
          <div className="flex flex-wrap justify-between gap-3"><Button onClick={() => router.push(incidentPath(locale, draftId))} variant="outline">{t("backToIncident")}</Button><Button isLoading={saving} type="submit">{t("saveContinue")}</Button></div>
        </form>
      </div>
    </main>
  );
}

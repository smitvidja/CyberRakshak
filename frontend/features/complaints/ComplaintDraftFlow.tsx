"use client";

import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";

import {Button} from "@/components/ui/Button";
import {StepIndicator} from "@/components/common/Workflow";
import {UploadDropzone} from "@/components/evidence/UploadDropzone";
import {TextArea, TextInput} from "@/components/ui/FormFields";
import {StatePanel, SurfaceCard} from "@/components/ui/Surface";
import {complaintCategoriesApi, complaintsApi, evidenceApi} from "@/lib/api/complaints";
import type {ApiRecord} from "@/lib/api/auth";
import {addComplaintEvidence, getAccessToken, getComplaintDraft, getReportCategoryHint, getReportMode, setComplaintDraft} from "@/lib/auth/citizen-session";

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
    incidentAt: asString(draft.incident_at).slice(0, 16),
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
  const [draft, setDraft] = useState<ApiRecord | null>(null);
  const [form, setForm] = useState<IncidentForm>(emptyIncidentForm);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [serviceError, setServiceError] = useState("");

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
          setDraft(cachedDraft.data);
          setForm(incidentFromDraft(cachedDraft.data));
        }

        if (isIdentifiedReport() && getAccessToken()) {
          const draftResult = await complaintsApi.getById(draftId, requestOptions());
          if (active && draftResult.ok) {
            setDraft(draftResult.data);
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
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function saveDraft(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
      incident_at: form.incidentAt || null,
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
    setComplaintDraft({data: result.data, id: savedDraftId});
    setDraft(result.data);
    setForm(incidentFromDraft(result.data));
    setMessage(t("saved"));
    setSaving(false);
    if (draftId === "new") {
      router.replace(incidentPath(locale, savedDraftId));
    }
  }

  if (loading) {
    return <main className="citizen-page shell-container py-8 sm:py-12"><StatePanel title={t("loadingTitle")} tone="loading">{t("loadingCopy")}</StatePanel></main>;
  }

  const savedDraftId = draftId === "new" ? null : draftId;
  return (
    <main className="citizen-page shell-container py-8 sm:py-12">
      <div className="mx-auto max-w-5xl space-y-6">
        <p className="eyebrow">{t("incidentEyebrow")}</p>
        <h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("incidentTitle")}</h1>
        <p className="max-w-3xl text-base leading-7 text-[var(--muted)]">{t("incidentIntro")}</p>
        <StepIndicator label={t("steps.label")} steps={workflowSteps(t, "incident")} />
        {serviceError ? <StatePanel title={t("errorTitle")} tone="error">{serviceError}</StatePanel> : null}
        {message ? <StatePanel title={t("savedTitle")} tone="success">{message}</StatePanel> : null}
        <form className="space-y-6" onSubmit={saveDraft} noValidate>
          <SurfaceCard heading={t("categoryTitle")}>
            <fieldset>
              <legend className="text-sm font-bold text-[var(--ink)]">{t("categoryLabel")}</legend>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {categories.map((category) => <button aria-pressed={form.categoryId === category.id} className={["min-h-24 rounded-[var(--radius)] border p-4 text-left transition-colors", form.categoryId === category.id ? "border-[var(--blue)] bg-[var(--blue-soft)]" : "border-[var(--border)] bg-white hover:bg-[#f5f8fb]"].join(" ")} key={category.id} onClick={() => updateField("categoryId", category.id)} type="button"><strong className="block text-sm text-[var(--navy)]">{category.name}</strong>{category.description ? <span className="mt-2 block text-xs leading-5 text-[var(--muted)]">{category.description}</span> : null}</button>)}
              </div>
              {errors.categoryId ? <p className="mt-2 text-sm font-medium text-[var(--danger)]" role="alert">{errors.categoryId}</p> : null}
            </fieldset>
          </SurfaceCard>
          <SurfaceCard heading={t("detailsTitle")}>
            <div className="grid gap-4 sm:grid-cols-2">
              <TextInput error={errors.title} id="incident-title" label={t("titleLabel")} onChange={(event) => updateField("title", event.target.value)} required value={form.title} />
              <TextInput id="incident-date" label={t("incidentAtLabel")} onChange={(event) => updateField("incidentAt", event.target.value)} type="datetime-local" value={form.incidentAt} />
              <TextInput error={errors.lossAmount} id="loss-amount" label={t("lossAmountLabel")} min="0" onChange={(event) => updateField("lossAmount", event.target.value)} step="0.01" type="number" value={form.lossAmount} />
              <div className="hidden sm:block" aria-hidden="true" />
            </div>
            <div className="mt-4"><TextArea description={t("descriptionHelp")} error={errors.description} id="incident-description" label={t("descriptionLabel")} onChange={(event) => updateField("description", event.target.value)} required value={form.description} /></div>
          </SurfaceCard>
          <SurfaceCard heading={t("locationTitle")}>
            <div className="grid gap-4 sm:grid-cols-3">
              <TextInput id="incident-city" label={t("cityLabel")} onChange={(event) => updateField("city", event.target.value)} value={form.city} />
              <TextInput id="incident-district" label={t("districtLabel")} onChange={(event) => updateField("district", event.target.value)} value={form.district} />
              <TextInput id="incident-state" label={t("stateLabel")} onChange={(event) => updateField("state", event.target.value)} value={form.state} />
            </div>
          </SurfaceCard>
          <div className="flex flex-wrap gap-3"><Button isLoading={saving} type="submit">{savedDraftId ? t("saveChanges") : t("saveDraft")}</Button>{savedDraftId ? <Button onClick={() => router.push(peoplePath(locale, savedDraftId))} variant="outline">{t("continuePeople")}</Button> : null}</div>
        </form>
        {savedDraftId && draft ? <EvidenceUploader complaintId={savedDraftId} /> : <StatePanel title={t("evidenceTitle")} tone="info">{t("evidenceAfterSave")}</StatePanel>}
      </div>
    </main>
  );
}

function EvidenceUploader({complaintId}: {complaintId: string}) {
  const t = useTranslations("complaintDraft");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [items, setItems] = useState<EvidenceItem[]>([]);
  const [uploading, setUploading] = useState(false);

  async function upload() {
    if (!file) {
      setError(t("evidenceFileRequired"));
      return;
    }
    setUploading(true);
    setError("");
    const payload = new FormData();
    payload.set("complaint_id", complaintId);
    payload.set("description", description);
    payload.set("file", file);
    const result = await evidenceApi.upload(payload, requestOptions());
    if (!result.ok) {
      setError(t("evidenceError"));
      setUploading(false);
      return;
    }
    const evidenceItem = {fileName: asString(result.data.file_name) || file.name, fileSize: Number(result.data.file_size) || file.size, id: asString(result.data.id)};
    setItems((current) => [...current, evidenceItem]);
    addComplaintEvidence(complaintId, evidenceItem);
    setDescription("");
    setFile(null);
    setUploading(false);
  }

  return <SurfaceCard heading={t("evidenceTitle")}><UploadDropzone accept=".pdf,.png,.jpg,.jpeg" browseLabel={t("browseEvidence")} description={t("evidenceDescription")} error={error} id="complaint-evidence" maxSizeLabel={t("evidenceSize")} onFilesSelected={(files) => { setFile(files[0] ?? null); setError(""); }} title={file ? file.name : t("evidenceUploadTitle")} /><div className="mt-4 max-w-xl"><TextInput id="evidence-description" label={t("evidenceDescriptionLabel")} onChange={(event) => setDescription(event.target.value)} value={description} /></div><Button className="mt-4" disabled={!file} isLoading={uploading} onClick={upload}>{t("uploadEvidence")}</Button>{items.length > 0 ? <ul className="mt-4 divide-y divide-[var(--border)] rounded-[var(--radius)] border border-[var(--border)]">{items.map((item) => <li className="px-4 py-3 text-sm text-[var(--ink)]" key={item.id}>{t("evidenceUploaded", {fileName: item.fileName, fileSize: item.fileSize})}</li>)}</ul> : null}</SurfaceCard>;
}

export function ComplaintPeopleStep({draftId}: {draftId: string}) {
  const t = useTranslations("complaintDraft");
  const locale = useLocale();
  const router = useRouter();
  const [people, setPeople] = useState<PersonForm[]>([emptyPersonForm]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      const cachedDraft = getComplaintDraft();
      if (cachedDraft?.id === draftId) {
        setPeople(peopleFromDraft(cachedDraft.data));
      }
      if (isIdentifiedReport() && getAccessToken()) {
        const result = await complaintsApi.getById(draftId, requestOptions());
        if (!active) {
          return;
        }
        if (result.ok) {
          setPeople(peopleFromDraft(result.data));
          setComplaintDraft({data: result.data, id: draftId});
        } else if (!cachedDraft) {
          setError(t("draftUnavailable"));
        }
      } else if (!cachedDraft) {
        setError(t("draftUnavailable"));
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

  function updatePerson(index: number, field: keyof PersonForm, value: string) {
    setPeople((current) => current.map((person, personIndex) => personIndex === index ? {...person, [field]: value} : person));
  }

  function removePerson(index: number) {
    setPeople((current) => current.length === 1 ? [emptyPersonForm] : current.filter((_, personIndex) => personIndex !== index));
  }

  async function savePeople(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const suspects = people.filter((person) => Object.values(person).some(Boolean)).map((person) => ({alias: person.alias || null, contact_details: person.contactDetails || null, description: person.description || null, name: person.name || null}));
    const result = await complaintsApi.updateDraft(draftId, {suspects}, requestOptions());
    if (!result.ok) {
      setError(t("saveError"));
      setSaving(false);
      return;
    }
    setComplaintDraft({data: result.data, id: draftId});
    setPeople(peopleFromDraft(result.data));
    setSaved(true);
    setSaving(false);
  }

  if (loading) {
    return <main className="citizen-page shell-container py-8 sm:py-12"><StatePanel title={t("loadingTitle")} tone="loading">{t("loadingCopy")}</StatePanel></main>;
  }

  return <main className="citizen-page shell-container py-8 sm:py-12"><div className="mx-auto max-w-5xl space-y-6"><p className="eyebrow">{t("peopleEyebrow")}</p><h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("peopleTitle")}</h1><p className="max-w-3xl text-base leading-7 text-[var(--muted)]">{t("peopleIntro")}</p><StepIndicator label={t("steps.label")} steps={workflowSteps(t, "people")} />{error ? <StatePanel title={t("errorTitle")} tone="error">{error}</StatePanel> : null}{saved ? <StatePanel action={<div className="flex flex-wrap gap-2"><Button onClick={() => router.push(incidentPath(locale, draftId))} variant="outline">{t("backToIncident")}</Button><Button onClick={() => router.push(reviewPath(locale, draftId))}>{t("continueReview")}</Button></div>} title={t("peopleSavedTitle")} tone="success">{t("peopleSavedCopy")}</StatePanel> : null}<form className="space-y-5" onSubmit={savePeople}><SurfaceCard heading={t("peopleFormTitle")}><div className="space-y-6">{people.map((person, index) => <fieldset className="border-b border-[var(--border)] pb-6 last:border-0 last:pb-0" key={index}><legend className="text-sm font-bold text-[var(--navy)]">{t("personNumber", {number: index + 1})}</legend><div className="mt-3 grid gap-4 sm:grid-cols-2"><TextInput id={"person-name-" + index} label={t("personName")} onChange={(event) => updatePerson(index, "name", event.target.value)} value={person.name} /><TextInput id={"person-alias-" + index} label={t("personAlias")} onChange={(event) => updatePerson(index, "alias", event.target.value)} value={person.alias} /><TextInput id={"person-contact-" + index} label={t("personContact")} onChange={(event) => updatePerson(index, "contactDetails", event.target.value)} value={person.contactDetails} /><div className="flex items-end"><Button onClick={() => removePerson(index)} variant="outline">{t("removePerson")}</Button></div></div><div className="mt-4"><TextArea id={"person-description-" + index} label={t("personDescription")} onChange={(event) => updatePerson(index, "description", event.target.value)} value={person.description} /></div></fieldset>)}</div><div className="mt-5 flex flex-wrap gap-3"><Button onClick={() => setPeople((current) => [...current, emptyPersonForm])} variant="outline">{t("addPerson")}</Button><Button isLoading={saving} type="submit">{t("savePeople")}</Button></div></SurfaceCard></form></div></main>;
}
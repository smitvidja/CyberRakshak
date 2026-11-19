"use client";

import {useState} from "react";
import {useTranslations} from "next-intl";
import {CheckCircle2, Pencil, XCircle} from "lucide-react";

import {Button} from "@/components/ui/Button";
import {CheckboxField, SelectField} from "@/components/ui/FormFields";
import {cyberWarriorsApi} from "@/lib/api/cyber-warriors";
import {getWarriorToken} from "@/lib/auth/warrior-session";

// "Availability & Preferences" from the Step 14 profile reference. The values are the
// fixed codes the API validates (backend/app/schemas/cyber_warrior.py); labels are
// translated here, so nothing free-text is stored.
export const AVAILABILITY_CODES = ["UNDER_5", "5_TO_10", "10_TO_15", "15_TO_20", "OVER_20"] as const;
export const TASK_CODES = ["REPORT_REVIEW", "EVIDENCE_ANALYSIS", "AWARENESS", "OSINT_RESEARCH", "VICTIM_SUPPORT", "TRANSLATION"] as const;
export const COMMUNICATION_CODES = ["EMAIL", "PORTAL", "SMS"] as const;

export type WarriorPreferences = {
  availability: string | null;
  preferred_communication: string[] | null;
  preferred_tasks: string[] | null;
  willing_to_volunteer: boolean | null;
};

function toggle(list: string[], code: string, on: boolean) {
  return on ? [...list.filter((item) => item !== code), code] : list.filter((item) => item !== code);
}

// Keep the fixed display order regardless of the order the boxes were ticked in.
function ordered(list: string[], codes: readonly string[]) {
  return codes.filter((code) => list.includes(code));
}

export function WarriorAvailabilitySection({onSaved, preferences}: {onSaved: (next: WarriorPreferences) => void; preferences: WarriorPreferences}) {
  const t = useTranslations("warriorProfile");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [draft, setDraft] = useState({
    availability: preferences.availability ?? "",
    communication: preferences.preferred_communication ?? [],
    tasks: preferences.preferred_tasks ?? [],
    willing: preferences.willing_to_volunteer === null ? "" : preferences.willing_to_volunteer ? "yes" : "no"
  });
  const notProvided = t("notProvided");

  function startEditing() {
    setDraft({
      availability: preferences.availability ?? "",
      communication: preferences.preferred_communication ?? [],
      tasks: preferences.preferred_tasks ?? [],
      willing: preferences.willing_to_volunteer === null ? "" : preferences.willing_to_volunteer ? "yes" : "no"
    });
    setError("");
    setSaved(false);
    setEditing(true);
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getWarriorToken();
    if (!token) return;
    setSaving(true);
    setError("");
    const payload: WarriorPreferences = {
      availability: draft.availability || null,
      preferred_communication: draft.communication.length ? ordered(draft.communication, COMMUNICATION_CODES) : null,
      preferred_tasks: draft.tasks.length ? ordered(draft.tasks, TASK_CODES) : null,
      willing_to_volunteer: draft.willing === "" ? null : draft.willing === "yes"
    };
    const result = await cyberWarriorsApi.updateMine(payload, {accessToken: token});
    setSaving(false);
    if (!result.ok) {
      setError(t("preferencesError"));
      return;
    }
    onSaved(payload);
    setEditing(false);
    setSaved(true);
  }

  const taskLabels = (preferences.preferred_tasks ?? []).map((code) => t(`taskOptions.${code}`));
  const channelLabels = (preferences.preferred_communication ?? []).map((code) => t(`communicationOptions.${code}`));

  return (
    <section className="warrior-profile-section" aria-labelledby="warrior-availability-title">
      <div className="warrior-profile-section-head">
        <h2 id="warrior-availability-title">{t("availabilityTitle")}</h2>
        {!editing ? (
          <button aria-label={t("editPreferencesLabel")} className="warrior-section-edit" onClick={startEditing} type="button">
            <Pencil aria-hidden="true" size={15} />{t("editPreferences")}
          </button>
        ) : null}
      </div>

      {!editing ? (
        <>
          <dl className="warrior-profile-fact-grid warrior-availability-grid">
            <div><dt>{t("availabilityLabel")}</dt><dd>{preferences.availability ? t(`availabilityOptions.${preferences.availability}`) : notProvided}</dd></div>
            <div><dt>{t("preferredTasksLabel")}</dt><dd>{taskLabels.length ? taskLabels.join(", ") : notProvided}</dd></div>
            <div><dt>{t("preferredCommunicationLabel")}</dt><dd>{channelLabels.length ? channelLabels.join(", ") : notProvided}</dd></div>
            <div>
              <dt>{t("willingToVolunteerLabel")}</dt>
              <dd>
                {preferences.willing_to_volunteer === null ? notProvided : preferences.willing_to_volunteer
                  ? <span className="warrior-yes-no is-yes"><CheckCircle2 aria-hidden="true" size={16} />{t("yes")}</span>
                  : <span className="warrior-yes-no is-no"><XCircle aria-hidden="true" size={16} />{t("no")}</span>}
              </dd>
            </div>
          </dl>
          {saved ? <p className="warrior-inline-success" role="status">{t("preferencesSaved")}</p> : null}
        </>
      ) : (
        <form className="warrior-availability-form" onSubmit={save}>
          <div className="warrior-availability-form-row">
            <SelectField
              id="warrior-availability"
              label={t("availabilityLabel")}
              onChange={(event) => setDraft((current) => ({...current, availability: event.target.value}))}
              options={[{label: notProvided, value: ""}, ...AVAILABILITY_CODES.map((code) => ({label: t(`availabilityOptions.${code}`), value: code}))]}
              value={draft.availability}
            />
            <SelectField
              id="warrior-willing"
              label={t("willingToVolunteerLabel")}
              onChange={(event) => setDraft((current) => ({...current, willing: event.target.value}))}
              options={[{label: notProvided, value: ""}, {label: t("yes"), value: "yes"}, {label: t("no"), value: "no"}]}
              value={draft.willing}
            />
          </div>
          <fieldset className="warrior-choice-group">
            <legend>{t("preferredTasksLabel")}</legend>
            {TASK_CODES.map((code) => (
              <CheckboxField
                checked={draft.tasks.includes(code)}
                id={"warrior-task-" + code}
                key={code}
                label={t(`taskOptions.${code}`)}
                onCheckedChange={(event) => setDraft((current) => ({...current, tasks: toggle(current.tasks, code, event.target.checked)}))}
              />
            ))}
          </fieldset>
          <fieldset className="warrior-choice-group">
            <legend>{t("preferredCommunicationLabel")}</legend>
            {COMMUNICATION_CODES.map((code) => (
              <CheckboxField
                checked={draft.communication.includes(code)}
                id={"warrior-channel-" + code}
                key={code}
                label={t(`communicationOptions.${code}`)}
                onCheckedChange={(event) => setDraft((current) => ({...current, communication: toggle(current.communication, code, event.target.checked)}))}
              />
            ))}
          </fieldset>
          {error ? <p className="warrior-form-error" role="alert">{error}</p> : null}
          <div className="warrior-availability-actions">
            <Button onClick={() => setEditing(false)} type="button" variant="outline">{t("cancelEdit")}</Button>
            <Button isLoading={saving} type="submit">{t("savePreferences")}</Button>
          </div>
        </form>
      )}
    </section>
  );
}

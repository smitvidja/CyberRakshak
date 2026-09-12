"use client";

import {useCallback, useEffect, useMemo, useState} from "react";
import {useTranslations} from "next-intl";

import {Button} from "@/components/ui/Button";
import {SelectField, TextArea, TextInput} from "@/components/ui/FormFields";
import {ResponsiveDataList, type DataListRow} from "@/components/ui/ResponsiveDataList";
import {StatePanel, StatusChip, SurfaceCard} from "@/components/ui/Surface";
import {authApi} from "@/lib/api/auth";
import {
  adminApi,
  type KnowledgeGap,
  type KnowledgeGapStatus
} from "@/lib/api/backoffice";
import {clearAdminSession, getAdminEmail, getAdminToken, setAdminSession} from "@/lib/auth/admin-session";

const STATUSES: KnowledgeGapStatus[] = ["OPEN", "REVIEWED", "ACTIONED", "DISMISSED"];

function toneFor(status: KnowledgeGapStatus) {
  if (status === "ACTIONED") return "success" as const;
  if (status === "DISMISSED") return "neutral" as const;
  if (status === "REVIEWED") return "info" as const;
  return "warning" as const;
}

function formatDate(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString();
}

export function KnowledgeGapsConsole() {
  const t = useTranslations("adminKnowledgeGaps");
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [signingIn, setSigningIn] = useState(false);
  const [authError, setAuthError] = useState("");

  const [gaps, setGaps] = useState<KnowledgeGap[]>([]);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [statusFilter, setStatusFilter] = useState("OPEN");
  const [minOccurrences, setMinOccurrences] = useState("1");
  const [notice, setNotice] = useState("");

  const [openGapId, setOpenGapId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  // Runs once on mount so a reload does not force another sign-in.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- browser-only session read; a lazy initializer would disagree with the server snapshot
    setToken(getAdminToken());
    setEmail(getAdminEmail() ?? "");
  }, []);

  const load = useCallback(
    async (accessToken: string) => {
      setLoading(true);
      setListError("");
      const result = await adminApi.listKnowledgeGaps(
        {
          status: statusFilter === "ALL" ? undefined : statusFilter,
          minOccurrences: Number(minOccurrences) || 1
        },
        {accessToken}
      );
      setLoading(false);
      if (!result.ok) {
        // A rejected token is the common case here, and leaving a stale one in
        // storage would loop the operator through an empty table forever.
        if (result.error.status === 401 || result.error.status === 403) {
          clearAdminSession();
          setToken(null);
          setAuthError(t("sessionExpired"));
          return;
        }
        setListError(result.error.message ?? t("loadFailed"));
        return;
      }
      setGaps(result.data);
    },
    [minOccurrences, statusFilter, t]
  );

  // The fetch is started from outside the synchronous effect body: load() flips
  // the loading flag before its first await, and doing that inline makes React
  // re-render during the effect.
  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    void Promise.resolve().then(() => {
      if (!cancelled) void load(token);
    });
    return () => { cancelled = true; };
  }, [load, token]);

  async function signIn(event: React.FormEvent) {
    event.preventDefault();
    setSigningIn(true);
    setAuthError("");
    const result = await authApi.login({email, password});
    setSigningIn(false);
    if (!result.ok) {
      setAuthError(result.error.message ?? t("signInFailed"));
      return;
    }
    setAdminSession(result.data.access_token, email);
    setPassword("");
    setToken(result.data.access_token);
  }

  const applyStatus = useCallback(async (gap: KnowledgeGap, status: KnowledgeGapStatus) => {
    if (!token) return;
    setSaving(true);
    setNotice("");
    const result = await adminApi.updateKnowledgeGapStatus(
      gap.id,
      {status, resolution_note: note.trim() ? note.trim() : null},
      {accessToken: token}
    );
    setSaving(false);
    if (!result.ok) {
      setListError(result.error.message ?? t("updateFailed"));
      return;
    }
    setOpenGapId(null);
    setNote("");
    setNotice(t("updated", {status}));
    void load(token);
  }, [load, note, t, token]);

  const rows = useMemo<DataListRow[]>(
    () =>
      gaps.map((gap) => ({
        id: gap.id,
        values: {
          question: (
            <div className="space-y-1">
              <p className="font-semibold text-[var(--navy)]">{gap.sample_question}</p>
              <p className="text-xs text-[var(--muted)]">
                {t("seenBetween", {first: formatDate(gap.first_seen_at), last: formatDate(gap.last_seen_at)})}
              </p>
            </div>
          ),
          occurrences: <span className="text-base font-bold text-[var(--navy)]">{gap.occurrences}</span>,
          domain: (
            <div className="space-y-1">
              <p>{gap.crime_domain}</p>
              {gap.knowledge_domain ? <p className="text-xs text-[var(--muted)]">{gap.knowledge_domain}</p> : null}
              <p className="text-xs text-[var(--muted)]">{gap.language}</p>
            </div>
          ),
          status: (
            <div className="space-y-2">
              <StatusChip label={gap.status} tone={toneFor(gap.status)} />
              {gap.resolution_note ? <p className="text-xs text-[var(--muted)]">{gap.resolution_note}</p> : null}
            </div>
          ),
          action:
            openGapId === gap.id ? (
              <div className="space-y-2">
                <TextArea
                  id={"gap-note-" + gap.id}
                  label={t("noteLabel")}
                  description={t("noteHelp")}
                  maxLength={2000}
                  onChange={(event) => setNote(event.target.value)}
                  rows={3}
                  value={note}
                />
                <div className="flex flex-wrap gap-2">
                  {STATUSES.filter((status) => status !== gap.status).map((status) => (
                    <Button
                      isLoading={saving}
                      key={status}
                      onClick={() => void applyStatus(gap, status)}
                      variant="outline"
                    >
                      {status}
                    </Button>
                  ))}
                  <Button onClick={() => { setOpenGapId(null); setNote(""); }} variant="outline">
                    {t("cancel")}
                  </Button>
                </div>
              </div>
            ) : (
              <Button onClick={() => { setOpenGapId(gap.id); setNote(gap.resolution_note ?? ""); }} variant="outline">
                {t("review")}
              </Button>
            )
        }
      })),
    [applyStatus, gaps, note, openGapId, saving, t]
  );

  if (!token) {
    return (
      <main className="shell-container py-8 sm:py-12">
        <div className="mx-auto max-w-md">
          <p className="eyebrow">{t("eyebrow")}</p>
          <h1 className="mt-2 text-3xl font-bold text-[var(--navy)]">{t("signInTitle")}</h1>
          <p className="mt-3 text-base leading-7 text-[var(--muted)]">{t("signInCopy")}</p>
          <SurfaceCard className="mt-6" heading={t("signInHeading")}>
            <form className="space-y-5" onSubmit={signIn}>
              <TextInput
                autoComplete="username"
                id="admin-email"
                label={t("email")}
                onChange={(event) => setEmail(event.target.value)}
                required
                type="email"
                value={email}
              />
              <TextInput
                autoComplete="current-password"
                id="admin-password"
                label={t("password")}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
              {authError ? <p className="text-sm font-bold text-[var(--danger)]" role="alert">{authError}</p> : null}
              <Button isLoading={signingIn} type="submit">{t("signIn")}</Button>
            </form>
          </SurfaceCard>
        </div>
      </main>
    );
  }

  return (
    <main className="shell-container py-8 sm:py-12">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="eyebrow">{t("eyebrow")}</p>
            <h1 className="mt-2 text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("title")}</h1>
            <p className="mt-3 max-w-3xl text-base leading-7 text-[var(--muted)]">{t("intro")}</p>
          </div>
          <Button onClick={() => { clearAdminSession(); setToken(null); setGaps([]); }} variant="outline">
            {t("signOut")}
          </Button>
        </div>

        <StatePanel title={t("corpusRuleTitle")} tone="info">{t("corpusRuleCopy")}</StatePanel>

        <SurfaceCard className="mt-6" heading={t("filtersHeading")}>
          <div className="grid gap-5 sm:grid-cols-3">
            <SelectField
              id="gap-status-filter"
              label={t("statusFilter")}
              onChange={(event) => setStatusFilter(event.target.value)}
              options={[{label: t("allStatuses"), value: "ALL"}, ...STATUSES.map((status) => ({label: status, value: status}))]}
              value={statusFilter}
            />
            <TextInput
              id="gap-min-occurrences"
              inputMode="numeric"
              label={t("minOccurrences")}
              onChange={(event) => setMinOccurrences(event.target.value.replace(/\D/g, ""))}
              value={minOccurrences}
            />
            <div className="flex items-end">
              <Button isLoading={loading} onClick={() => token && void load(token)}>{t("refresh")}</Button>
            </div>
          </div>
        </SurfaceCard>

        {notice ? <StatePanel title={t("updatedTitle")} tone="success">{notice}</StatePanel> : null}
        {listError ? <p className="mt-4 text-sm font-bold text-[var(--danger)]" role="alert">{listError}</p> : null}

        <div className="mt-6">
          <ResponsiveDataList
            caption={t("tableCaption")}
            columns={[
              {key: "question", label: t("columnQuestion")},
              {key: "occurrences", label: t("columnOccurrences")},
              {key: "domain", label: t("columnDomain")},
              {key: "status", label: t("columnStatus")},
              {key: "action", label: t("columnAction")}
            ]}
            emptyMessage={loading ? t("loading") : t("empty")}
            rows={rows}
          />
        </div>
      </div>
    </main>
  );
}

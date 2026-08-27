"use client";

import {useState} from "react";
import {useTranslations} from "next-intl";
import {BookOpen, Gavel, Megaphone, Search, ShieldCheck, Sparkles, Wrench} from "lucide-react";

import {WarriorShellPage} from "./WarriorAppShell";

const categories = [
  {icon: ShieldCheck, key: "safety"},
  {icon: BookOpen, key: "reporting"},
  {icon: Megaphone, key: "awareness"},
  {icon: Wrench, key: "tools"},
  {icon: Gavel, key: "laws"},
  {icon: Sparkles, key: "training"}
] as const;

export function WarriorResources() {
  const t = useTranslations("warriorResources");
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const topics = ["tipPasswords", "tipPhishing", "tipReporting", "tipEvidence", "tipPrivacy"];
  const normalizedQuery = query.trim().toLowerCase();
  const visibleTopics = normalizedQuery
    ? topics.filter((topicKey) => (t(topicKey + "Title") + " " + t(topicKey + "Summary")).toLowerCase().includes(normalizedQuery))
    : topics;

  return (
    <WarriorShellPage active="resources">
      <div className="warrior-dashboard-content warrior-full-width">
        <h1>{t("title")}</h1>
        <p>{t("copy")}</p>

        <div className="warrior-resource-search">
          <Search aria-hidden="true" size={17} />
          <input
            aria-label={t("searchPlaceholder")}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("searchPlaceholder")}
            type="search"
            value={query}
          />
        </div>

        <div className="warrior-resource-category-grid">
          {categories.map((category) => (
            <div className="warrior-resource-category-tile" key={category.key}>
              <span aria-hidden="true"><category.icon size={22} /></span>
              <strong>{t("category." + category.key)}</strong>
            </div>
          ))}
        </div>

        <section className="warrior-profile-section">
          <h2>{t("popularTitle")}</h2>
          {visibleTopics.length === 0 ? <p className="warrior-report-field-label">{t("noSearchResults")}</p> : null}
          <div className="warrior-resource-list">
            {visibleTopics.map((topicKey) => (
              <div className="warrior-resource-row" key={topicKey}>
                <button className="warrior-resource-row-toggle" onClick={() => setOpenKey((current) => (current === topicKey ? null : topicKey))} type="button">
                  <span><strong>{t(topicKey + "Title")}</strong><small>{t(topicKey + "Summary")}</small></span>
                  <span aria-hidden="true">{openKey === topicKey ? "−" : "+"}</span>
                </button>
                {openKey === topicKey ? <p className="warrior-resource-row-body">{t(topicKey + "Body")}</p> : null}
              </div>
            ))}
          </div>
          <p className="warrior-status-note">{t("moreComingNote")}</p>
        </section>
      </div>
    </WarriorShellPage>
  );
}

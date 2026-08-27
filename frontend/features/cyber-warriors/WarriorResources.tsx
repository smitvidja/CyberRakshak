"use client";

import {useState} from "react";
import {useTranslations} from "next-intl";
import {BookOpen, Gavel, Megaphone, ShieldCheck, Sparkles, Wrench} from "lucide-react";

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

  const topics = ["tipPasswords", "tipPhishing", "tipReporting", "tipEvidence", "tipPrivacy"];

  return (
    <WarriorShellPage active="resources">
      <div className="warrior-dashboard-content warrior-full-width">
        <h1>{t("title")}</h1>
        <p>{t("copy")}</p>

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
          <div className="warrior-resource-list">
            {topics.map((topicKey) => (
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

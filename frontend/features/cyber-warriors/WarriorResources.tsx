"use client";

import Image from "next/image";
import {useState} from "react";
import {useTranslations} from "next-intl";
import {BookOpen, Download, Gavel, Megaphone, PhoneCall, Search, ShieldCheck, Sparkles, Wrench, X} from "lucide-react";

import {WarriorShellPage} from "./WarriorAppShell";

// Awareness posters live in public/images/awareness (generated from the source art
// in demo-assets/Resources by backend/scripts/prepare_awareness_assets.py).
// `tall` marks portrait art so the grid can give it a taller frame instead of
// cropping the poster's headline or its helpline footer.
const awarenessPosters = [
  {slug: "identity-theft", tall: true},
  {slug: "qr-upi-scam", tall: true},
  {slug: "sim-swap-fraud", tall: true},
  {slug: "prepaid-task-scam", tall: true},
  {slug: "loan-app-harassment", tall: true},
  {slug: "matrimonial-scam", tall: true},
  {slug: "webcam-blackmail", tall: true},
  {slug: "misinformation", tall: true},
  {slug: "otp-remote-access", tall: false},
  {slug: "first-hour-after-fraud", tall: true}
] as const;

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
  const [openPoster, setOpenPoster] = useState<string | null>(null);

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
          <div className="warrior-awareness-head">
            <div>
              <h2>{t("awarenessTitle")}</h2>
              <p className="warrior-status-hint">{t("awarenessCopy")}</p>
            </div>
            <a className="warrior-awareness-download" download href="/docs/cyber-awareness-set.pdf">
              <Download aria-hidden="true" size={17} />
              {t("awarenessDownload")}
            </a>
          </div>

          <div className="warrior-awareness-grid">
            {awarenessPosters.map((poster) => (
              <button
                className={"warrior-awareness-card " + (poster.tall ? "is-tall" : "is-wide")}
                key={poster.slug}
                onClick={() => setOpenPoster(poster.slug)}
                type="button"
              >
                <Image
                  alt={t("poster." + poster.slug + "Title")}
                  className="warrior-awareness-image"
                  height={poster.tall ? 1200 : 491}
                  loading="lazy"
                  sizes="(max-width: 700px) 100vw, (max-width: 1100px) 45vw, 30vw"
                  src={"/images/awareness/" + poster.slug + ".webp"}
                  width={poster.tall ? 900 : 900}
                />
                <span className="warrior-awareness-caption">
                  <strong>{t("poster." + poster.slug + "Title")}</strong>
                  <small>{t("poster." + poster.slug + "Story")}</small>
                </span>
              </button>
            ))}
          </div>

          <p className="warrior-awareness-helpline">
            <PhoneCall aria-hidden="true" size={16} />
            {t("awarenessHelpline")}
          </p>
        </section>

        {openPoster ? (
          <div className="warrior-poster-backdrop" onClick={() => setOpenPoster(null)} role="presentation">
            <div
              aria-label={t("poster." + openPoster + "Title")}
              aria-modal="true"
              className="warrior-poster-modal"
              onClick={(event) => event.stopPropagation()}
              role="dialog"
            >
              <button aria-label={t("closePoster")} className="warrior-poster-close" onClick={() => setOpenPoster(null)} type="button">
                <X aria-hidden="true" size={18} />
              </button>
              <Image
                alt={t("poster." + openPoster + "Title")}
                className="warrior-poster-full"
                height={1200}
                sizes="(max-width: 700px) 92vw, 640px"
                src={"/images/awareness/" + openPoster + ".webp"}
                width={900}
              />
              <div className="warrior-poster-body">
                <h3>{t("poster." + openPoster + "Title")}</h3>
                <p>{t("poster." + openPoster + "Story")}</p>
                <p className="warrior-poster-advice"><ShieldCheck aria-hidden="true" size={16} />{t("poster." + openPoster + "Advice")}</p>
                <a className="warrior-poster-call" href="tel:1930"><PhoneCall aria-hidden="true" size={16} />{t("awarenessCall")}</a>
              </div>
            </div>
          </div>
        ) : null}

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

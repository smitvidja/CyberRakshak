import Link from "next/link";
import {hasLocale} from "next-intl";
import {getTranslations, setRequestLocale} from "next-intl/server";
import {notFound} from "next/navigation";
import {BarChart3, Flame, Map, PhoneCall, Sparkles} from "lucide-react";

import {routing} from "@/lib/i18n/routing";

type Props = {params: Promise<{locale: string}>};

// Deliberately a standalone route, separate from /resources - this was
// previously wired to the same warrior-dashboard Resources page as every other
// "Learning Corner"-style link, which was wrong on two counts: wrong content
// (Secure India is a crime-map feature, not the awareness posters) and wrong
// chrome (private warrior sidebar for a public teaser).
//
// No crime-map artwork is embedded here yet - it was shared as a chat image,
// which cannot be read as a file. This page is honest about being unbuilt
// rather than shipping a placeholder graphic with invented statistics.
export default async function SecureIndiaPage({params}: Props) {
  const {locale} = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  const t = await getTranslations({locale, namespace: "secureIndia"});

  const previewItems = [
    {icon: Map, key: "mapVisualizer"},
    {icon: BarChart3, key: "cityRankings"},
    {icon: Flame, key: "hotZones"},
    {icon: Sparkles, key: "linkedResources"}
  ] as const;

  return (
    <main className="shell-container secure-india-page">
      <header className="secure-india-hero">
        <span className="secure-india-badge">{t("upcomingBadge")}</span>
        <h1>{t("title")}</h1>
        <p>{t("copy")}</p>
      </header>

      <section className="secure-india-preview" aria-labelledby="secure-india-preview-title">
        <h2 id="secure-india-preview-title">{t("previewTitle")}</h2>
        <div className="secure-india-preview-grid">
          {previewItems.map(({icon: Icon, key}) => (
            <div className="secure-india-preview-tile" key={key}>
              <span aria-hidden="true"><Icon size={22} /></span>
              <strong>{t(`preview.${key}.title`)}</strong>
              <small>{t(`preview.${key}.copy`)}</small>
            </div>
          ))}
        </div>
        <p className="secure-india-mock-note">{t("mockDataNote")}</p>
      </section>

      <section className="secure-india-cta">
        <div>
          <strong>{t("ctaTitle")}</strong>
          <span>{t("ctaCopy")}</span>
        </div>
        <Link href={`/${locale}/resources`}>{t("ctaAction")}</Link>
      </section>

      <p className="secure-india-helpline">
        <PhoneCall aria-hidden="true" size={16} />
        {t("helplineNote")}
      </p>
    </main>
  );
}

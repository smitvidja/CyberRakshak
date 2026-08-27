import Image from "next/image";
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
// The preview graphic below is a full mockup of the planned page (a Bengaluru
// hot-zone heatmap), converted from demo-assets/Resources/secure-india-heatmap.png
// by backend/scripts/prepare_awareness_assets.py. It is shown as a screenshot
// preview, not live content: the feature underneath it does not exist yet, and
// every number visible in the image (complaint counts, resolution rate, city
// rankings) is invented for the mockup. The mockup itself already labels its
// numbers "Mock Data" / "Illustrative" - do not crop that labelling out, and
// do not let a future real integration reuse this image without replacing it.
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

      <section className="secure-india-screenshot" aria-labelledby="secure-india-screenshot-title">
        <h2 id="secure-india-screenshot-title">{t("screenshotTitle")}</h2>
        <p className="secure-india-screenshot-copy">{t("screenshotCopy")}</p>
        <div className="secure-india-screenshot-frame">
          <span className="secure-india-screenshot-chip">{t("upcomingBadge")}</span>
          <Image
            alt={t("screenshotAlt")}
            className="secure-india-screenshot-image"
            height={2093}
            sizes="(max-width: 700px) 100vw, 900px"
            src="/images/awareness/secure-india-preview-v1.webp"
            width={900}
          />
        </div>
        <p className="secure-india-mock-note">{t("screenshotMockNote")}</p>
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

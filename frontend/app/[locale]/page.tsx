import Image from "next/image";
import Link from "next/link";
import {hasLocale} from "next-intl";
import {getTranslations, setRequestLocale} from "next-intl/server";
import {notFound} from "next/navigation";
import { BookOpenCheck, ChevronRight, Siren } from "lucide-react";

import {routing} from "@/lib/i18n/routing";
import {
  DrawnBell,
  DrawnBulb,
  DrawnCap,
  DrawnClipboard,
  DrawnMegaphone,
  DrawnPhone,
  DrawnShield,
  DrawnWarrior
} from "@/components/ui/DrawnIcons";
import {SaathiMark} from "@/components/ui/SaathiMark";

type Props = {params: Promise<{locale: string}>};

type CategoryKey = "women" | "financial" | "identity" | "harassment" | "commerce" | "other";

const categoryAssets: Record<CategoryKey, string> = {
  women: "/images/home/categories/women-child.png",
  financial: "/images/home/categories/financial-fraud.png",
  identity: "/images/home/categories/identity-misuse.png",
  harassment: "/images/home/categories/online-harassment.png",
  commerce: "/images/home/categories/ecommerce-fraud.png",
  other: "/images/home/categories/other-concern.png"
};


export default async function LocaleHomePage({params}: Props) {
  const {locale} = await params;
  if (!hasLocale(routing.locales, locale)) notFound();

  setRequestLocale(locale);
  const t = await getTranslations({locale, namespace: "home"});
  const reportHref = `/${locale}/report-crime`;
  const trackHref = `/${locale}/complaints/track`;
  // Every "Learning Corner" entry point on this page used to point at #learning, a
  // same-page anchor that was never defined - clicking any of them did nothing.
  // Then it was pointed at the Cyber Warrior dashboard's /cyber-warrior/resources -
  // which meant a citizen clicking it landed inside the private warrior sidebar
  // (Dashboard / My Reports / My Application / Leaderboard / Log out). This is the
  // real fix: a standalone public page with no warrior chrome at all.
  const learningHref = `/${locale}/resources`;
  // Secure India is an unrelated, not-yet-built feature (a crime-map visualizer) -
  // it must never share a destination with Learning Corner. It previously did,
  // by mistake.
  const secureIndiaHref = `/${locale}/secure-india`;
  const categoryEntryHref = (category: string) => `${reportHref}?category=${category}`;
  const reportingHref = (mode: "anonymous" | "identified", category: string) => `${reportHref}?mode=${mode}&category=${category}`;
  const categories: CategoryKey[] = ["women", "financial", "identity", "harassment", "commerce", "other"];
  const updates = [
    {key: "fakeCalls", icon: DrawnPhone},
    {key: "advisory", icon: DrawnMegaphone},
    {key: "tips", icon: DrawnBulb}
  ] as const;
  // Cyber Saathi is no longer one tile among five - it is the panel in the hero,
  // because talking it through is the entry point this portal is actually for.
  const quickLinks = [
    {key: "warrior", href: `/${locale}/cyber-warrior`, icon: DrawnWarrior},
    {key: "learn", href: learningHref, icon: DrawnBell},
    {key: "secure", href: secureIndiaHref, icon: DrawnShield},
    {key: "track", href: trackHref, icon: DrawnClipboard}
  ] as const;

  return (
    <main className="home-portal">
      <section className="home-hero-band" aria-labelledby="home-title">
        <Image alt="" className="home-hero-image object-cover object-center" fill priority sizes="100vw" src="/images/home/cyber-safety-hero.png" />
        <div className="home-hero-veil" />
        <div className="shell-container home-hero-inner">
          <div className="home-hero-words">
            <p className="home-hero-eyebrow">{t("heroEyebrow")}</p>
            {/* Three staggered lines. They stay inside the one h1, so the
                accessible name is still the whole sentence - the stagger is
                layout, not content. */}
            <h1 id="home-title" className="home-hero-title">
              <span className="line line-a">{t("heroTitleA")}</span>
              <span className="line line-b">{t("heroTitleB")}</span>
              <span className="line line-c">{t("heroTitleC")}</span>
            </h1>
            <p className="home-hero-copy">{t("heroCopy")}</p>
            <div className="home-hero-actions">
              <Link className="portal-secondary-link" href={trackHref}>{t("trackAction")}</Link>
            </div>
          </div>

          {/* Named, with a presence dot and a sample exchange. A paragraph about an
              assistant is abstract; two bubbles are not. */}
          <aside className="home-saathi">
            <div className="home-saathi-id">
              <span aria-hidden="true" className="home-saathi-avatar"><SaathiMark size={30} strokeWidth={1.9} /></span>
              <span className="home-saathi-id-text">
                <span className="home-saathi-name">{t("heroSaathiName")}</span>
                <span className="home-saathi-status">{t("heroSaathiStatus")}</span>
              </span>
            </div>

            <p className="home-saathi-eyebrow">{t("heroSaathiEyebrow")}</p>
            <p className="home-saathi-title">{t("heroSaathiTitle")}</p>

            {/* Illustrative, not a transcript - kept generic and visibly static. */}
            <div className="home-saathi-thread" aria-hidden="true">
              <p className="home-saathi-bubble is-citizen">{t("heroSaathiSampleUser")}</p>
              <p className="home-saathi-bubble is-saathi">{t("heroSaathiSampleReply")}</p>
            </div>

            {/* The card used to be a poster about a chatbot. These are three real
                openings in a citizen's own words - the ones most people arrive
                with - so the card is a way in rather than an advertisement. */}
            <p className="home-saathi-chips-lead">{t("heroSaathiChipsLead")}</p>
            <div className="home-saathi-chips">
              {(["A", "B", "C"] as const).map((slot) => (
                <Link key={slot} className="home-saathi-chip" href={`/${locale}/cyber-saathi`}>
                  {t(`heroSaathiChip${slot}`)}
                </Link>
              ))}
            </div>

            <Link className="home-saathi-action" href={`/${locale}/cyber-saathi`}>
              {t("heroSaathiAction")}
              <ChevronRight aria-hidden="true" size={18} strokeWidth={2.4} />
            </Link>
            <p className="home-saathi-note">{t("heroSaathiNote")}</p>
          </aside>
        </div>
      </section>

      {/* One shelf, four segments. These were four tall cards carrying one line each. */}
      <div className="shell-container">
        <nav className="home-shelf" aria-label={t("quickLinksLabel")}>
          {quickLinks.map(({key, href, icon: Icon}) => (
            <Link key={key} href={href} className="home-shelf-item">
              <span aria-hidden="true" className={"home-shelf-icon" + (key === "learn" ? " is-alert" : "")}>
                <Icon size={21} strokeWidth={1.7} />
              </span>
              <span className="home-shelf-text">
                <span className="home-shelf-title">{t(`quick.${key}.title`)}</span>
                <span className="home-shelf-copy">{t(`quick.${key}.copy`)}</span>
              </span>
            </Link>
          ))}
        </nav>
      </div>

      <div className="shell-container">
        <section className="home-helpline" aria-label={t("helplineLabel")}>
          <a className="home-helpline-primary" href="tel:1930">
            <span aria-hidden="true" className="home-helpline-icon"><Siren size={22} strokeWidth={1.8} /></span>
            <span>
              <span className="home-helpline-number">1930</span>
              <span className="home-helpline-label">{t("helplinePrimary")}</span>
            </span>
          </a>
          <Link className="home-helpline-secondary" href={learningHref}>
            <span aria-hidden="true" className="home-helpline-icon is-quiet"><BookOpenCheck size={22} strokeWidth={1.8} /></span>
            <span>
              <span className="home-helpline-title">{t("helplineSecondaryTitle")}</span>
              <span className="home-helpline-label is-quiet">{t("helplineSecondary")}</span>
            </span>
            <ChevronRight aria-hidden="true" className="home-action-chevron" size={17} strokeWidth={2.2} />
          </Link>
        </section>
      </div>

      {/* Bento. The featured cell is the sensitive route, and it is the only one
          that offers a choice of how to file. */}
      <section className="shell-container home-section" aria-labelledby="report-categories">
        <div className="portal-section-heading mb-5">
          <span aria-hidden="true" />
          <h2 id="report-categories">{t("categoriesTitle")}</h2>
          <span aria-hidden="true" />
        </div>
        <div className="home-bento">
          {categories.map((category) => {
            const featured = category === "women";
            return (
              <article key={category} data-category={category} className={"home-bento-card" + (featured ? " is-featured" : "")}>
                <Link aria-label={t(`categories.${category}.title`)} className="home-bento-body" href={categoryEntryHref(category)}>
                  <span className="home-bento-media">
                    <Image alt="" className="object-contain p-1.5" fill sizes={featured ? "132px" : "72px"} src={categoryAssets[category]} />
                  </span>
                  <span className="home-bento-text">
                    {featured ? (
                      // Staggered, so the title uses the height this cell has
                      // rather than leaving it empty. The accessible name comes
                      // from the Link's aria-label, which carries the real title.
                      <span aria-hidden="true" className="home-bento-stack">
                        <span className="line">{t(`categories.${category}.displayA`)}</span>
                        <span className="line is-second">{t(`categories.${category}.displayB`)}</span>
                      </span>
                    ) : (
                      <span className="home-bento-title">{t(`categories.${category}.title`)}</span>
                    )}
                    <span className="home-bento-copy">{t(`categories.${category}.copy`)}</span>
                    {featured ? <span className="home-bento-reassure">{t(`categories.${category}.reassure`)}</span> : null}
                  </span>
                </Link>
                <div className="home-bento-actions">
                  <Link className="home-bento-cta" href={reportingHref(featured ? "anonymous" : "identified", category)}>
                    {featured ? t("anonymousAction") : t("reportAction")}
                    <ChevronRight aria-hidden="true" size={16} strokeWidth={2.4} />
                  </Link>
                  {featured ? (
                    <Link className="home-bento-cta is-quiet" href={reportingHref("identified", category)}>
                      {t("reportAction")}
                      <ChevronRight aria-hidden="true" size={16} strokeWidth={2.4} />
                    </Link>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {/* A board, not three articles: tag, headline, arrow - scan and click. */}
      <section className="shell-container home-section" aria-labelledby="updates-title">
        <div className="home-board">
          <div className="home-board-side">
            <p className="home-board-eyebrow">{t("updatesBoardLabel")}</p>
            <h2 id="updates-title" className="home-board-heading">{t("updatesTitle")}</h2>
            <p className="home-board-count">{t("updatesCount")}</p>
            <Link className="home-board-all" href={learningHref}>
              {t("viewUpdates")}
              <ChevronRight aria-hidden="true" size={15} strokeWidth={2.4} />
            </Link>
          </div>
          <ul className="home-board-list">
            {updates.map(({key, icon: Icon}) => (
              <li key={key}>
                <Link className="home-board-row" href={learningHref}>
                  <span aria-hidden="true" className="home-board-icon"><Icon size={19} strokeWidth={1.7} /></span>
                  <span className="home-board-row-text">
                    <span className="home-board-tag">{t(`updates.${key}.tag`)}</span>
                    <span className="home-board-title">{t(`updates.${key}.title`)}</span>
                    <span className="home-board-copy">{t(`updates.${key}.copy`)}</span>
                  </span>
                  <ChevronRight aria-hidden="true" className="home-board-chevron" size={17} strokeWidth={2.2} />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section id="learning" className="shell-container home-section">
        <div className="home-learning">
          <span aria-hidden="true" className="home-learning-icon"><DrawnCap size={27} strokeWidth={1.6} /></span>
          <div className="home-learning-text">
            <h2>{t("learningTitle")}</h2>
            <p>{t("learningCopy")}</p>
          </div>
          <Link className="portal-outline-link" href={learningHref}>{t("learningAction")}</Link>
        </div>
      </section>
    </main>
  );
}

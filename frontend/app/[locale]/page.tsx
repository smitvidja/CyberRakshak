import Image from "next/image";
import Link from "next/link";
import {hasLocale} from "next-intl";
import {getTranslations, setRequestLocale} from "next-intl/server";
import {notFound} from "next/navigation";
import {BellRing, BookOpenCheck, ClipboardCheck, GraduationCap, Lightbulb, Megaphone, PhoneCall, ShieldCheck, Siren, UserRoundPlus} from "lucide-react";

import {routing} from "@/lib/i18n/routing";

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
    {key: "fakeCalls", icon: PhoneCall},
    {key: "advisory", icon: Megaphone},
    {key: "tips", icon: Lightbulb}
  ] as const;
  const quickLinks = [
    {key: "warrior", href: `/${locale}/cyber-warrior`, icon: UserRoundPlus},
    {key: "learn", href: learningHref, icon: BellRing},
    {key: "secure", href: secureIndiaHref, icon: ShieldCheck},
    {key: "track", href: trackHref, icon: ClipboardCheck}
  ] as const;

  return (
    <main className="home-portal overflow-x-hidden bg-[#f5f8fc] pb-10">
      <section className="mx-auto max-w-[1440px] px-4 py-4 sm:px-6 lg:px-8">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.95fr)_minmax(292px,0.82fr)]">
          <section className="home-hero relative min-h-[292px] overflow-hidden rounded-[8px] bg-[#062d68]" aria-labelledby="home-title">
            <Image alt="" className="object-cover object-center" fill priority sizes="(max-width: 1024px) 100vw, 70vw" src="/images/home/cyber-safety-hero.png" />
            <div className="absolute inset-0 bg-[#052552]/80" />
            <div className="relative flex min-h-[292px] max-w-2xl flex-col justify-center px-6 py-7 text-white sm:px-9">
              <p className="mb-3 text-xs font-bold uppercase tracking-[0.14em] text-sky-100">{t("heroEyebrow")}</p>
              <h1 id="home-title" className="max-w-xl text-[2rem] font-bold leading-[1.12] sm:text-[2.45rem]">{t("heroTitle")}</h1>
              <p className="mt-4 max-w-lg text-[15px] leading-6 text-sky-50 sm:text-base sm:leading-7">{t("heroCopy")}</p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link className="portal-primary-link" href={reportHref}>{t("reportAction")}</Link>
                <Link className="portal-secondary-link" href={trackHref}>{t("trackAction")}</Link>
              </div>
            </div>
          </section>

          <aside className="grid gap-2 lg:grid-rows-4" aria-label={t("quickLinksLabel")}>
            {quickLinks.map(({key, href, icon: Icon}) => (
              <Link key={key} href={href} className="portal-action-card group flex min-h-[66px] items-center gap-3 rounded-[8px] border border-slate-200 bg-white px-4 py-3 shadow-[0_2px_9px_rgb(15_42_74_/_0.08)]">
                <span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-[#bfd9f2] bg-[#edf6ff] text-[#075bbf]"><Icon size={20} strokeWidth={1.8} /></span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[15px] font-bold leading-5 text-[#092a58]">{t(`quick.${key}.title`)}</span>
                  <span className="mt-0.5 block text-xs leading-5 text-slate-600">{t(`quick.${key}.copy`)}</span>
                </span>
                <span aria-hidden="true" className="text-lg text-[#315274] transition-transform duration-150 group-hover:translate-x-0.5">&gt;</span>
              </Link>
            ))}
          </aside>
        </div>

        <section className="mt-3 grid overflow-hidden rounded-[8px] bg-[#073d87] text-white sm:grid-cols-2" aria-label={t("helplineLabel")}>
          <a className="support-action flex min-h-[64px] items-center gap-3 px-5 py-3 sm:px-8" href="tel:1930">
            <span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/70"><Siren size={21} strokeWidth={1.8} /></span>
            <span><span className="block text-xl font-bold">1930</span><span className="text-sm text-blue-100">{t("helplinePrimary")}</span></span>
          </a>
          <Link className="support-action flex min-h-[64px] items-center gap-3 border-t border-white/20 px-5 py-3 sm:border-l sm:border-t-0 sm:px-8" href={learningHref}>
            <span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/70"><BookOpenCheck size={21} strokeWidth={1.8} /></span>
            <span><span className="block text-base font-bold">{t("helplineSecondaryTitle")}</span><span className="text-sm text-blue-100">{t("helplineSecondary")}</span></span>
          </Link>
        </section>
      </section>

      <section className="mx-auto grid max-w-[1440px] gap-5 px-4 sm:px-6 xl:grid-cols-[minmax(0,1fr)_282px] xl:px-8">
        <section aria-labelledby="report-categories">
          <div className="portal-section-heading mb-4">
            <span aria-hidden="true" />
            <h2 id="report-categories">{t("categoriesTitle")}</h2>
            <span aria-hidden="true" />
          </div>
          <div className="report-category-grid grid grid-flow-dense gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {categories.map((category) => (
              <article key={category} className="report-category-card group flex min-w-0 flex-col rounded-[8px] border border-slate-200 bg-white p-3 shadow-[0_2px_9px_rgb(15_42_74_/_0.08)]">
                <Link aria-label={t(`categories.${category}.title`)} className="report-category-card-entry flex flex-1 flex-col rounded-[6px]" href={categoryEntryHref(category)}>
                  <span className="category-media relative aspect-[4/3] overflow-hidden rounded-[6px] border border-[#e3eef8] bg-[#f7fbff]">
                    <Image alt="" className="object-contain p-2 transition-transform duration-200 group-hover:scale-[1.03]" fill sizes="(max-width: 640px) 90vw, (max-width: 1280px) 30vw, 14vw" src={categoryAssets[category]} />
                  </span>
                  <h3 className="mt-3 text-[15px] font-bold leading-5 text-[#092a58]">{t(`categories.${category}.title`)}</h3>
                  <p className="mt-1.5 flex-1 text-[12px] leading-[1.5] text-slate-600">{t(`categories.${category}.copy`)}</p>
                </Link>
                <div className="mt-3 grid gap-1.5">
                  <Link className="report-card-action" href={reportingHref(category === "women" ? "anonymous" : "identified", category)}>{category === "women" ? t("anonymousAction") : t("reportAction")}</Link>
                  {category === "women" ? <Link className="report-card-action report-card-action-secondary" href={reportingHref("identified", category)}>{t("reportAction")}</Link> : null}
                </div>
              </article>
            ))}
          </div>
        </section>

        <aside className="portal-updates rounded-[8px] border border-slate-200 bg-white p-5 shadow-[0_2px_9px_rgb(15_42_74_/_0.08)]" aria-labelledby="updates-title">
          <div className="flex items-center justify-between gap-3 border-b border-slate-200 pb-3">
            <h2 id="updates-title" className="text-lg font-bold text-[#063d86]">{t("updatesTitle")}</h2>
            <Link className="text-xs font-bold text-[#075bbf] hover:underline" href={learningHref}>{t("viewUpdates")}</Link>
          </div>
          <div className="divide-y divide-slate-200">
            {updates.map(({key, icon: Icon}) => (
              <article key={key} className="flex gap-3 py-4">
                <span aria-hidden="true" className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-blue-50 text-[#075bbf]"><Icon size={18} strokeWidth={1.8} /></span>
                <div><h3 className="text-sm font-bold text-slate-900">{t(`updates.${key}.title`)}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t(`updates.${key}.copy`)}</p><Link className="mt-1 inline-block text-xs font-bold text-[#075bbf] hover:underline" href={learningHref}>{t("readMore")}</Link></div>
              </article>
            ))}
          </div>
          <Link className="mt-2 block rounded-[6px] bg-[#075bbf] px-4 py-3 text-center text-sm font-bold text-white transition-colors hover:bg-[#064b9d]" href={learningHref}>{t("viewUpdates")}</Link>
        </aside>
      </section>

      <section id="learning" className="mx-auto mt-7 max-w-[1440px] px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4 rounded-[8px] border border-blue-100 bg-[#edf6ff] px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4"><span aria-hidden="true" className="grid h-12 w-12 place-items-center rounded-[6px] bg-[#075bbf] text-white"><GraduationCap size={24} strokeWidth={1.8} /></span><div><h2 className="text-lg font-bold text-[#063d86]">{t("learningTitle")}</h2><p className="mt-1 text-sm text-slate-600">{t("learningCopy")}</p></div></div>
          <Link className="portal-outline-link w-fit" href={learningHref}>{t("learningAction")}</Link>
        </div>
      </section>
    </main>
  );
}

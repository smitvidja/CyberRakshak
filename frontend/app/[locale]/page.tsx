import Image from "next/image";
import Link from "next/link";
import {hasLocale} from "next-intl";
import {getTranslations, setRequestLocale} from "next-intl/server";
import {notFound} from "next/navigation";

import {routing} from "@/lib/i18n/routing";

type Props = {params: Promise<{locale: string}>};

export default async function LocaleHomePage({params}: Props) {
  const {locale} = await params;
  if (!hasLocale(routing.locales, locale)) notFound();

  setRequestLocale(locale);
  const t = await getTranslations({locale, namespace: "home"});
  const reportHref = `/${locale}/report-crime`;
  const trackHref = `/${locale}/complaints/track`;
  const reportingHref = (mode: "anonymous" | "identified", category: string) => `${reportHref}?mode=${mode}&category=${category}`;

  const quickLinks = [
    {key: "warrior", href: `/${locale}/cyber-warrior`, mark: "CW"},
    {key: "learn", href: "#learning", mark: "LE"},
    {key: "track", href: trackHref, mark: "TR"},
    {key: "report", href: reportHref, mark: "RP"}
  ] as const;

  const categories = ["women", "financial", "identity", "harassment", "commerce", "other"] as const;
  const updates = ["fakeCalls", "advisory", "tips"] as const;

  return (
    <main className="bg-slate-50 pb-8">
      <section className="mx-auto max-w-[1500px] px-4 py-3 sm:px-6 lg:px-8">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,2.15fr)_minmax(300px,0.85fr)]">
          <section className="relative h-[248px] overflow-hidden rounded-lg bg-[#062d68] lg:h-[264px]" aria-labelledby="home-title">
            <Image
              src="/images/home/cyber-safety-hero.png"
              alt=""
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 70vw"
              className="object-cover object-center"
            />
            <div className="absolute inset-0 bg-[#062044]/75" />
            <div className="relative flex h-full max-w-2xl flex-col justify-center px-6 py-6 text-white sm:px-9">
              <p className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-sky-100">{t("heroEyebrow")}</p>
              <h1 id="home-title" className="max-w-xl text-3xl font-bold leading-tight sm:text-4xl">{t("heroTitle")}</h1>
              <p className="mt-4 max-w-lg text-base leading-7 text-sky-50 sm:text-lg">{t("heroCopy")}</p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link href={reportHref} className="rounded-lg bg-white px-5 py-3 text-sm font-bold text-[#064fae] shadow-sm transition hover:bg-sky-50">{t("reportAction")}</Link>
                <Link href={trackHref} className="rounded-lg border border-white px-5 py-3 text-sm font-bold text-white transition hover:bg-white/10">{t("trackAction")}</Link>
              </div>
            </div>
          </section>

          <aside className="grid grid-rows-4 gap-2" aria-label={t("quickLinksLabel")}>
            {quickLinks.map(({key, href, mark}) => (
              <Link key={key} href={href} className="group flex min-h-[58px] items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm transition hover:border-blue-300 hover:bg-blue-50">
                <span aria-hidden="true" className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-blue-50 text-xs font-bold text-[#075bbf]">{mark}</span>
                <span className="min-w-0 flex-1">
                  <span className="block text-base font-bold text-slate-900">{t(`quick.${key}.title`)}</span>
                  <span className="mt-1 block text-sm leading-5 text-slate-600">{t(`quick.${key}.copy`)}</span>
                </span>
                <span aria-hidden="true" className="text-xl font-medium text-slate-500 transition group-hover:translate-x-0.5">&gt;</span>
              </Link>
            ))}
          </aside>
        </div>

        <section className="mt-3 grid overflow-hidden rounded-lg bg-[#073d87] text-white sm:grid-cols-2" aria-label={t("helplineLabel")}>
          <a href="tel:1930" className="flex min-h-[58px] items-center gap-3 px-5 py-3 transition hover:bg-[#0a4c9f] sm:px-8">
            <span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/60 text-lg">19</span>
            <span><span className="block text-xl font-bold">1930</span><span className="text-sm text-blue-100">{t("helplinePrimary")}</span></span>
          </a>
          <Link href="#learning" className="flex min-h-20 items-center gap-4 border-t border-white/20 px-5 py-4 transition hover:bg-[#0a4c9f] sm:border-l sm:border-t-0 sm:px-8">
            <span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/60 text-sm font-bold">CS</span>
            <span><span className="block text-base font-bold">{t("helplineSecondaryTitle")}</span><span className="text-sm text-blue-100">{t("helplineSecondary")}</span></span>
          </Link>
        </section>
      </section>

      <section className="mx-auto grid max-w-[1500px] gap-4 px-4 sm:px-6 xl:grid-cols-[minmax(0,1fr)_270px] xl:px-8">
        <section aria-labelledby="report-categories">
          <div className="mb-4 flex items-center gap-3">
            <span className="h-px flex-1 bg-blue-200" />
            <h2 id="report-categories" className="text-lg font-bold text-[#063d86]">{t("categoriesTitle")}</h2>
            <span className="h-px flex-1 bg-blue-200" />
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {categories.map((category, index) => (
              <article key={category} className="flex min-h-[182px] flex-col rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                <span aria-hidden="true" className={`grid h-12 w-12 place-items-center rounded-full text-sm font-bold ${["bg-rose-50 text-rose-700", "bg-emerald-50 text-emerald-700", "bg-amber-50 text-amber-700", "bg-violet-50 text-violet-700", "bg-sky-50 text-sky-700", "bg-slate-100 text-slate-700"][index]}`}>{["WC", "FR", "ID", "OH", "EC", "OT"][index]}</span>
                <h3 className="mt-4 text-base font-bold leading-5 text-slate-900">{t(`categories.${category}.title`)}</h3>
                <p className="mt-2 flex-1 text-sm leading-5 text-slate-600">{t(`categories.${category}.copy`)}</p>
                <div className="mt-3 grid gap-1.5">
                  <Link href={reportingHref(category === "women" ? "anonymous" : "identified", category)} className="rounded-md bg-[#075bbf] px-2 py-2 text-center text-xs font-bold text-white transition hover:bg-[#064b9d]">{category === "women" ? t("anonymousAction") : t("reportAction")}</Link>
                  {category === "women" && <Link href={reportingHref("identified", category)} className="rounded-md border border-[#075bbf] px-2 py-2 text-center text-xs font-bold text-[#075bbf] transition hover:bg-blue-50">{t("reportAction")}</Link>}
                </div>
              </article>
            ))}
          </div>
        </section>

        <aside className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm" aria-labelledby="updates-title">
          <div className="flex items-center justify-between gap-3 border-b border-slate-200 pb-3">
            <h2 id="updates-title" className="text-lg font-bold text-[#063d86]">{t("updatesTitle")}</h2>
            <Link href="#learning" className="text-xs font-bold text-[#075bbf] hover:underline">{t("viewUpdates")}</Link>
          </div>
          <div className="divide-y divide-slate-200">
            {updates.map((update, index) => (
              <article key={update} className="flex gap-3 py-4">
                <span aria-hidden="true" className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-blue-50 text-xs font-bold text-[#075bbf]">{["01", "02", "03"][index]}</span>
                <div><h3 className="text-sm font-bold text-slate-900">{t(`updates.${update}.title`)}</h3><p className="mt-1 text-xs leading-5 text-slate-600">{t(`updates.${update}.copy`)}</p><Link href="#learning" className="mt-1 inline-block text-xs font-bold text-[#075bbf] hover:underline">{t("readMore")}</Link></div>
              </article>
            ))}
          </div>
          <Link href="#learning" className="mt-2 block rounded-lg bg-[#075bbf] px-4 py-3 text-center text-sm font-bold text-white transition hover:bg-[#064b9d]">{t("viewUpdates")}</Link>
        </aside>
      </section>

      <section id="learning" className="mx-auto mt-7 max-w-[1500px] px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4 rounded-lg border border-blue-100 bg-blue-50 px-6 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4"><span aria-hidden="true" className="grid h-12 w-12 place-items-center rounded-lg bg-[#075bbf] text-sm font-bold text-white">LC</span><div><h2 className="text-lg font-bold text-[#063d86]">{t("learningTitle")}</h2><p className="mt-1 text-sm text-slate-600">{t("learningCopy")}</p></div></div>
          <Link href={`/${locale}/cyber-warrior`} className="w-fit rounded-lg border border-[#075bbf] px-4 py-2 text-sm font-bold text-[#075bbf] transition hover:bg-white">{t("learningAction")}</Link>
        </div>
      </section>
    </main>
  );
}

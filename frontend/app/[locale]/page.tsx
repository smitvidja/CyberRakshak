import Link from "next/link";
import { hasLocale } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { routing } from "@/lib/i18n/routing";

type LocalePageProps = {
  params: Promise<{ locale: string }>;
};

export default async function LocaleHomePage({
  params,
}: LocalePageProps) {
  const { locale } = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);

  const t = await getTranslations({ locale, namespace: "common" });
  const navigation = await getTranslations({
    locale,
    namespace: "navigation",
  });

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <section className="w-full max-w-xl border border-[var(--border)] bg-[var(--surface)] p-8 shadow-sm">
        <p className="text-sm font-medium text-teal-800">
          {t("foundationLabel")}
        </p>
        <h1 className="mt-3 text-3xl font-semibold">{t("projectName")}</h1>
        <p className="mt-4 leading-7 text-slate-700">
          {t("foundationMessage")}
        </p>
        <p className="mt-4 text-sm text-slate-600">
          {t("activeLanguage", {
            language: t(["languages", locale].join(".")),
          })}
        </p>
        <nav
          aria-label={navigation("languageSelector")}
          className="mt-8 flex flex-wrap gap-3"
        >
          {routing.locales.map((supportedLocale) => (
            <Link
              aria-current={locale === supportedLocale ? "page" : undefined}
              className="border border-[var(--border)] px-4 py-2 text-sm font-medium hover:bg-slate-100"
              href={"/" + supportedLocale}
              key={supportedLocale}
            >
              {t(["languages", supportedLocale].join("."))}
            </Link>
          ))}
        </nav>
      </section>
    </main>
  );
}
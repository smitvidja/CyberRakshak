import {hasLocale} from "next-intl";
import {getTranslations, setRequestLocale} from "next-intl/server";
import {notFound} from "next/navigation";
import Link from "next/link";

import {routing} from "@/lib/i18n/routing";

type Props = {params: Promise<{locale: string}>};
export default async function LocaleHomePage({params}: Props) {
  const {locale} = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  const t = await getTranslations({locale, namespace: "home"});
  return <main className="shell-container shell-placeholder"><section><p className="eyebrow">{t("eyebrow")}</p><h1>{t("title")}</h1><p>{t("copy")}</p><div className="placeholder-actions"><Link href={"/" + locale + "/report-crime"}>{t("reportAction")}</Link><Link href={"/" + locale + "/cyber-warrior"}>{t("warriorAction")}</Link></div></section></main>;
}

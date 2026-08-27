import Link from "next/link";
import {hasLocale} from "next-intl";
import {getTranslations, setRequestLocale} from "next-intl/server";
import {notFound} from "next/navigation";
import {AlertTriangle, FileSearch, PhoneCall, ShieldCheck, UserRoundPlus} from "lucide-react";

import {routing} from "@/lib/i18n/routing";

type Props = {params: Promise<{locale: string}>};

// Deliberately carries no invented contact details - no fabricated email address,
// office address, or support number. 1930 is the real, publicly published Indian
// cybercrime helpline; everything else here points at flows that exist in this
// prototype. Adding a plausible-looking "support@..." inbox nobody monitors would
// be worse than omitting it.
export default async function ContactPage({params}: Props) {
  const {locale} = await params;
  if (!hasLocale(routing.locales, locale)) notFound();

  setRequestLocale(locale);
  const t = await getTranslations({locale, namespace: "contact"});

  const routes = [
    {key: "report", href: `/${locale}/report-crime`, icon: ShieldCheck},
    {key: "track", href: `/${locale}/complaints/track`, icon: FileSearch},
    {key: "suspect", href: `/${locale}/suspects/report`, icon: AlertTriangle},
    {key: "warrior", href: `/${locale}/cyber-warrior`, icon: UserRoundPlus}
  ] as const;

  return (
    <main className="contact-page shell-container">
      <header className="contact-intro">
        <p className="eyebrow">{t("eyebrow")}</p>
        <h1>{t("title")}</h1>
        <p>{t("copy")}</p>
      </header>

      <section className="contact-helpline" aria-labelledby="contact-helpline-title">
        <span className="contact-helpline-icon" aria-hidden="true"><PhoneCall size={26} /></span>
        <div>
          <h2 id="contact-helpline-title">{t("helplineTitle")}</h2>
          <p>{t("helplineCopy")}</p>
        </div>
        <a href="tel:1930">{t("helplineAction")}</a>
      </section>

      <section aria-labelledby="contact-routes-title">
        <h2 className="contact-section-title" id="contact-routes-title">{t("routesTitle")}</h2>
        <div className="contact-route-grid">
          {routes.map(({key, href, icon: Icon}) => (
            <Link className="contact-route-card" href={href} key={key}>
              <span aria-hidden="true"><Icon size={21} /></span>
              <strong>{t(`routes.${key}.title`)}</strong>
              <small>{t(`routes.${key}.copy`)}</small>
            </Link>
          ))}
        </div>
      </section>

      <section className="contact-disclosure" aria-labelledby="contact-disclosure-title">
        <h2 id="contact-disclosure-title">{t("disclosureTitle")}</h2>
        <p>{t("disclosureCopy")}</p>
      </section>
    </main>
  );
}

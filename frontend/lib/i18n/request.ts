import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { notFound } from "next/navigation";

import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  const requestedLocale = await requestLocale;

  if (!hasLocale(routing.locales, requestedLocale)) {
    notFound();
  }

  return {
    locale: requestedLocale,
    messages: (await import("../../messages/" + requestedLocale + ".json"))
      .default,
  };
});
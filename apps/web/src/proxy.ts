import { type NextRequest, NextResponse } from "next/server";
import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";
import { previewAccess } from "./preview-access";

const localize = createMiddleware(routing);

export default function proxy(request: NextRequest) {
  // Publishing the research preview must never silently disable access control
  // when an operator forgets the optional local credential file on recreation.
  const required =
    process.env.PROPERTY_PLATFORM_PREVIEW_ACCESS_REQUIRED ??
    (process.env.PROPERTY_PLATFORM_ENABLE_LOCAL_PREVIEW === "1"
      ? "1"
      : undefined);
  const access = previewAccess(request.headers.get("authorization"), {
    required,
    digest: process.env.PROPERTY_PLATFORM_PREVIEW_ACCESS_DIGEST,
  });
  const path = request.nextUrl.pathname;
  const response =
    access === "unauthorized"
      ? new NextResponse(null, {
          status: 401,
          headers: {
            "WWW-Authenticate":
              'Basic realm="Property Platform Preview", charset="UTF-8"',
          },
        })
      : access === "unavailable"
        ? new NextResponse(null, { status: 503 })
        : /^\/(?:api|_next|_vercel)(?:\/|$)/.test(path) || path.includes(".")
          ? NextResponse.next()
          : localize(request);
  if (required !== undefined && required !== "0") {
    response.headers.set("Cache-Control", "private, no-store");
    response.headers.set("X-Robots-Tag", "noindex, nofollow, noarchive");
  }
  return response;
}

export const config = {
  matcher: ["/:path*"],
};

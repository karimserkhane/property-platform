import { createHash, timingSafeEqual } from "node:crypto";

// Temporary preview access only; this is not application identity or staff auth.
export function previewAccess(
  authorization: string | null,
  environment: { required?: string; digest?: string },
): "allowed" | "unauthorized" | "unavailable" {
  if (environment.required === undefined || environment.required === "0")
    return "allowed";
  if (
    environment.required !== "1" ||
    !/^[a-f0-9]{64}$/.test(environment.digest ?? "")
  )
    return "unavailable";
  const encoded = /^Basic ([A-Za-z0-9+/]{1,2048}={0,2})$/i.exec(
    authorization ?? "",
  )?.[1];
  if (!encoded) return "unauthorized";
  const credentials = Buffer.from(encoded, "base64");
  if (credentials.toString("base64") !== encoded) return "unauthorized";
  const actual = createHash("sha256").update(credentials).digest();
  return timingSafeEqual(actual, Buffer.from(environment.digest ?? "", "hex"))
    ? "allowed"
    : "unauthorized";
}

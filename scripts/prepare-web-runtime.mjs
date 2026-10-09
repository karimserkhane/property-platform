import { cp, mkdir } from "node:fs/promises";

const webRoot = new URL("../apps/web/", import.meta.url);
const destination = new URL(".next/standalone/apps/web/.next/static/", webRoot);

await mkdir(destination, { recursive: true });
await cp(new URL(".next/static/", webRoot), destination, { recursive: true });

try {
  await cp(
    new URL("public/", webRoot),
    new URL(".next/standalone/apps/web/public/", webRoot),
    { recursive: true },
  );
} catch (error) {
  if (error.code !== "ENOENT") throw error;
}

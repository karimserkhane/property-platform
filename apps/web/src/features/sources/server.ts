import "server-only";

import { cache } from "react";
import { readPreview } from "@/features/atlas/server";
import { readSourceFreshnessData, readSourceSitesData } from "./data";

export const readSourceSites = cache(() => readSourceSitesData(readPreview));
export const readSourceFreshness = cache(() =>
  readSourceFreshnessData(readPreview),
);

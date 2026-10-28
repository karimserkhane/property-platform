import "server-only";

import { cache } from "react";
import { readPreview } from "@/features/atlas/server";
import { readSourceSitesData } from "./data";

export const readSourceSites = cache(() => readSourceSitesData(readPreview));

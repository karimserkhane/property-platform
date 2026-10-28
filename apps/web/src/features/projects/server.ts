import "server-only";

import { cache } from "react";
import { readPreview } from "@/features/atlas/server";
import { readProjectData } from "./data";
import { readDeliveryHistoryData } from "./delivery";

export const readProject = cache((slug: string) =>
  readProjectData(slug, readPreview),
);

export const readDeliveryHistory = cache((key: string) =>
  readDeliveryHistoryData(key, readPreview),
);

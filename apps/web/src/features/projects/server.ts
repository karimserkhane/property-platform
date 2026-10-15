import "server-only";

import { cache } from "react";
import { readPreview } from "@/features/atlas/server";
import { readProjectData } from "./data";

export const readProject = cache((slug: string) =>
  readProjectData(slug, readPreview),
);

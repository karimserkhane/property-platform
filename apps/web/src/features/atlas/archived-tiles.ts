import { addProtocol } from "maplibre-gl";

let registered = false;

export function registerArchivedTiles() {
  if (registered) return;
  registered = true;
  addProtocol("archive", async (request, controller) => {
    const path = request.url.replace(/^archive:\/\//, "");
    if (
      !/^(openfreemap|sentinel-worldcover-202[01])\/\d{1,2}\/\d{1,5}\/\d{1,5}$/.test(
        path,
      )
    )
      throw new Error("Invalid archived tile");
    // A first visit can queue a tile for Prefect. Never switch source while it
    // is being acquired; cancellation stops polling when the map moves away.
    const deadline = Date.now() + 180000;
    while (!controller.signal.aborted) {
      const response = await fetch(`/api/atlas/satellite/${path}`, {
        signal: controller.signal,
      });
      if (response.status === 200)
        return { data: await response.arrayBuffer() };
      if (response.status !== 202 || Date.now() >= deadline)
        throw new Error("Archived tile unavailable");
      await new Promise<void>((resolve, reject) => {
        const cancel = () => {
          clearTimeout(timer);
          reject(controller.signal.reason);
        };
        const timer = setTimeout(() => {
          controller.signal.removeEventListener("abort", cancel);
          resolve();
        }, 3000);
        controller.signal.addEventListener("abort", cancel, { once: true });
        if (controller.signal.aborted) {
          controller.signal.removeEventListener("abort", cancel);
          cancel();
        }
      });
    }
    throw controller.signal.reason;
  });
}

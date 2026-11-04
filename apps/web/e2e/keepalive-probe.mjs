// TEMPORARY (A31): measures keep-alive failures between Node fetch and gunicorn in CI; removed before merge.
// Many clients reusing Node fetch keep-alive sockets with idle gaps around gunicorn's
// keep-alive close. One summary line; failures are counted by cause.
const [url, workersArg, perWorkerArg, band] = process.argv.slice(2);
const workers = Number(workersArg), perWorker = Number(perWorkerArg);
const [low, high] = band.split("-").map(Number);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
let requests = 0, failures = 0;
const causes = {};
async function worker() {
  for (let i = 0; i < perWorker; i++) {
    await sleep(low + Math.random() * (high - low));
    requests++;
    try {
      const response = await fetch(url, { cache: "no-store" });
      await response.arrayBuffer();
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
    } catch (error) {
      failures++;
      const cause = error.cause?.code ?? error.cause?.message ?? error.message;
      causes[cause] = (causes[cause] ?? 0) + 1;
    }
  }
}
const started = Date.now();
await Promise.all(Array.from({ length: workers }, worker));
console.log(JSON.stringify({ url, node: process.version, requests, failures, causes, gap: band, seconds: Math.round((Date.now() - started) / 1000) }));

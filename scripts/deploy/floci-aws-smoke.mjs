#!/usr/bin/env node

import { createHash } from "node:crypto";

const endpointUrl = (
  process.env.AWS_ENDPOINT_URL ?? "http://localhost:4566"
).replace(/\/$/, "");
const bucket = process.env.STIX_FLOCI_BUCKET ?? "stix-fde-artifacts";
const objectKey =
  process.env.STIX_FLOCI_OBJECT_KEY ?? "smoke/stix-fde-smoke.txt";
const body = "stix floci fde deterministic smoke\n";
const timeoutMs = Number.parseInt(
  process.env.STIX_FLOCI_SMOKE_TIMEOUT_MS ?? "15000",
  10,
);

async function request(path, init = {}, acceptedStatuses = []) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${endpointUrl}${path}`, {
      ...init,
      signal: controller.signal,
    });
    const text = await response.text();

    if (!response.ok && !acceptedStatuses.includes(response.status)) {
      throw new Error(
        [
          `${init.method ?? "GET"} ${path} failed with HTTP ${response.status}`,
          text.trim(),
        ]
          .filter(Boolean)
          .join("\n"),
      );
    }

    return { status: response.status, text };
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error(
        `${init.method ?? "GET"} ${path} timed out after ${timeoutMs}ms`,
      );
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

try {
  assertLocalEndpoint(endpointUrl);

  await request(`/${bucket}`, { method: "PUT" }, [409]);
  await request(`/${bucket}/${objectKey}`, { method: "PUT", body });
  const objectBody = await request(`/${bucket}/${objectKey}`);
  const bucketList = await request(`/${bucket}`);
  const rootList = await request("/");

  const result = {
    ok: true,
    endpointUrl,
    bucket,
    objectKey,
    bodySha256: sha256(body),
    objectRoundTrip: objectBody.text === body,
    bucketListedObject: bucketList.text.includes(objectKey),
    rootListedBucket: rootList.text.includes(bucket),
  };

  if (
    !result.objectRoundTrip ||
    !result.bucketListedObject ||
    !result.rootListedBucket
  ) {
    throw new Error(
      `Floci S3 smoke failed invariant checks: ${JSON.stringify(result)}`,
    );
  }

  console.log(
    JSON.stringify(
      {
        ...result,
        outputSha256: sha256(
          canonicalJson({
            bucket: result.bucket,
            objectKey: result.objectKey,
            bodySha256: result.bodySha256,
          }),
        ),
      },
      null,
      2,
    ),
  );
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}

function assertLocalEndpoint(value) {
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`AWS_ENDPOINT_URL must be a valid URL, received: ${value}`);
  }

  const localHosts = new Set([
    "localhost",
    "127.0.0.1",
    "::1",
    "[::1]",
    "floci",
    "stix-floci",
    "localhost.floci.io",
  ]);

  if (!localHosts.has(parsed.hostname)) {
    throw new Error(
      `Refusing to run FDE smoke against non-local AWS endpoint: ${value}. Doctrine/FDE Floci drills must use the local emulator.`,
    );
  }
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function canonicalJson(value) {
  return `${JSON.stringify(value, Object.keys(value).sort())}\n`;
}

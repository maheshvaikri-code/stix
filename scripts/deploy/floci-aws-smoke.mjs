#!/usr/bin/env node

import { randomUUID } from 'node:crypto';

const endpointUrl = (process.env.AWS_ENDPOINT_URL ?? 'http://localhost:4566').replace(/\/$/, '');
const bucket = process.env.STIX_FLOCI_BUCKET ?? 'stix-fde-artifacts';
const objectKey = `smoke/${new Date().toISOString().replaceAll(':', '-')}-${randomUUID()}.txt`;
const body = 'stix floci fde smoke\n';

async function request(path, init = {}) {
  const response = await fetch(`${endpointUrl}${path}`, init);
  const text = await response.text();

  if (!response.ok) {
    throw new Error(
      [
        `${init.method ?? 'GET'} ${path} failed with HTTP ${response.status}`,
        text.trim(),
      ]
        .filter(Boolean)
        .join('\n'),
    );
  }

  return text;
}

try {
  await request(`/${bucket}`, { method: 'PUT' });
  await request(`/${bucket}/${objectKey}`, { method: 'PUT', body });
  const objectBody = await request(`/${bucket}/${objectKey}`);
  const bucketList = await request(`/${bucket}`);
  const rootList = await request('/');

  console.log(
    JSON.stringify(
      {
        ok: true,
        endpointUrl,
        bucket,
        objectKey,
        objectRoundTrip: objectBody === body,
        bucketListedObject: bucketList.includes(objectKey),
        rootListedBucket: rootList.includes(bucket),
      },
      null,
      2,
    ),
  );
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
